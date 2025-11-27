"""
Service for monitoring system health and sending alerts.
"""
import logging
import shutil
from datetime import timedelta
from typing import Dict, List, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from celery import current_app

from ..models_alerts import AlertRule, Alert, SystemMetric
from .ffmpeg_wrapper import FFmpegWrapper

logger = logging.getLogger(__name__)


class AlertService:
    """Service for system monitoring and alerting."""
    
    def __init__(self):
        self.celery_app = current_app
    
    def check_all_rules(self):
        """
        Check all active alert rules.
        
        This method should be called periodically (e.g., every 5 minutes).
        """
        logger.info("[ALERTS] Starting alert rule check")
        
        active_rules = AlertRule.objects.filter(is_active=True)
        alerts_triggered = 0
        
        for rule in active_rules:
            try:
                if self._should_check_rule(rule):
                    if self._check_rule(rule):
                        alerts_triggered += 1
            except Exception as e:
                logger.error(f"[ALERTS] Error checking rule {rule.name}: {e}")
        
        logger.info(f"[ALERTS] Check completed, {alerts_triggered} alerts triggered")
        return alerts_triggered
    
    def _should_check_rule(self, rule: AlertRule) -> bool:
        """Check if enough time has passed since last check."""
        last_alert = Alert.objects.filter(
            rule=rule,
            status='active'
        ).order_by('-created_at').first()
        
        if not last_alert:
            return True
        
        cooldown_period = timedelta(minutes=rule.cooldown_minutes)
        return timezone.now() - last_alert.created_at > cooldown_period
    
    def _check_rule(self, rule: AlertRule) -> bool:
        """Check a specific alert rule and trigger alert if needed."""
        current_value = self._get_current_value(rule.alert_type)
        
        if current_value is None:
            logger.warning(f"[ALERTS] Could not get value for {rule.alert_type}")
            return False
        
        # Record metric
        SystemMetric.record(rule.alert_type, current_value)
        
        # Check threshold
        if self._threshold_exceeded(rule, current_value):
            return self._trigger_alert(rule, current_value)
        
        # Resolve existing alerts if threshold is no longer exceeded
        self._resolve_alerts_if_needed(rule, current_value)
        return False
    
    def _get_current_value(self, alert_type: str) -> Optional[float]:
        """Get current value for the alert type."""
        try:
            if alert_type == 'queue_size':
                return self._get_queue_size()
            elif alert_type == 'error_rate':
                return self._get_error_rate()
            elif alert_type == 'ffmpeg_unavailable':
                return 0.0 if FFmpegWrapper.check_ffmpeg_available() else 1.0
            elif alert_type == 'disk_space':
                return self._get_disk_usage_percent()
            elif alert_type == 'processing_time':
                return self._get_avg_processing_time()
            else:
                logger.warning(f"[ALERTS] Unknown alert type: {alert_type}")
                return None
        except Exception as e:
            logger.error(f"[ALERTS] Error getting value for {alert_type}: {e}")
            return None
    
    def _get_queue_size(self) -> float:
        """Get current queue size."""
        try:
            inspect = self.celery_app.control.inspect()
            scheduled = inspect.scheduled()
            active = inspect.active()
            
            total_tasks = 0
            if scheduled:
                for worker, tasks in scheduled.items():
                    total_tasks += len(tasks)
            if active:
                for worker, tasks in active.items():
                    total_tasks += len(tasks)
            
            return float(total_tasks)
        except Exception as e:
            logger.warning(f"[ALERTS] Could not get queue size: {e}")
            return 0.0
    
    def _get_error_rate(self) -> float:
        """Get error rate in last hour (percentage)."""
        from ..models import Video
        
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        total_videos = Video.objects.filter(
            updated_at__gte=one_hour_ago,
            processing_status__in=['completed', 'failed', 'error']
        ).count()
        
        if total_videos == 0:
            return 0.0
        
        failed_videos = Video.objects.filter(
            updated_at__gte=one_hour_ago,
            processing_status__in=['failed', 'error']
        ).count()
        
        return (failed_videos / total_videos) * 100
    
    def _get_disk_usage_percent(self) -> float:
        """Get disk usage percentage."""
        try:
            total, used, free = shutil.disk_usage(settings.MEDIA_ROOT)
            return (used / total) * 100
        except Exception as e:
            logger.warning(f"[ALERTS] Could not get disk usage: {e}")
            return 0.0
    
    def _get_avg_processing_time(self) -> float:
        """Get average processing time in last 24 hours (minutes)."""
        return SystemMetric.get_average('processing_time_avg', hours=24) or 0.0
    
    def _threshold_exceeded(self, rule: AlertRule, current_value: float) -> bool:
        """Check if threshold is exceeded."""
        if rule.alert_type in ['queue_size', 'error_rate', 'disk_space', 'processing_time']:
            return current_value > rule.threshold_value
        elif rule.alert_type == 'ffmpeg_unavailable':
            return current_value > 0  # 1.0 means unavailable
        return False
    
    def _trigger_alert(self, rule: AlertRule, current_value: float) -> bool:
        """Trigger an alert."""
        message = self._generate_alert_message(rule, current_value)
        
        alert = Alert.objects.create(
            rule=rule,
            message=message,
            current_value=current_value,
            metadata={
                'timestamp': timezone.now().isoformat(),
                'threshold': rule.threshold_value,
            }
        )
        
        logger.warning(f"[ALERTS] Alert triggered: {message}")
        
        # Send notifications
        self._send_notifications(alert)
        
        return True
    
    def _generate_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """Generate human-readable alert message."""
        if rule.alert_type == 'queue_size':
            return f"Queue size is high: {int(current_value)} tasks (threshold: {int(rule.threshold_value)})"
        elif rule.alert_type == 'error_rate':
            return f"Error rate is high: {current_value:.1f}% (threshold: {rule.threshold_value:.1f}%)"
        elif rule.alert_type == 'ffmpeg_unavailable':
            return "FFmpeg is not available - video processing will fail"
        elif rule.alert_type == 'disk_space':
            return f"Disk usage is high: {current_value:.1f}% (threshold: {rule.threshold_value:.1f}%)"
        elif rule.alert_type == 'processing_time':
            return f"Processing time is high: {current_value:.1f} min (threshold: {rule.threshold_value:.1f} min)"
        else:
            return f"Alert: {rule.name} - Value: {current_value} (threshold: {rule.threshold_value})"
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications."""
        # Send email
        if alert.rule.send_email and alert.rule.get_email_list():
            self._send_email_alert(alert)
        
        # Send webhook
        if alert.rule.webhook_url:
            self._send_webhook_alert(alert)
    
    def _send_email_alert(self, alert: Alert):
        """Send email notification."""
        try:
            subject = f"[TubeCMS Alert] {alert.rule.name}"
            message = f"""
Alert: {alert.rule.name}
Severity: {alert.rule.get_severity_display()}
Message: {alert.message}
Time: {alert.created_at}

Alert ID: {alert.id}
Rule: {alert.rule.get_alert_type_display()}
Threshold: {alert.rule.threshold_value}
Current Value: {alert.current_value}

Please check the system and acknowledge this alert in the admin panel.
"""
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=alert.rule.get_email_list(),
                fail_silently=False,
            )
            
            alert.email_sent = True
            alert.save()
            logger.info(f"[ALERTS] Email sent for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"[ALERTS] Failed to send email for alert {alert.id}: {e}")
    
    def _send_webhook_alert(self, alert: Alert):
        """Send webhook notification."""
        try:
            import requests
            
            payload = {
                'alert_id': alert.id,
                'rule_name': alert.rule.name,
                'severity': alert.rule.severity,
                'message': alert.message,
                'current_value': alert.current_value,
                'threshold': alert.rule.threshold_value,
                'timestamp': alert.created_at.isoformat(),
            }
            
            response = requests.post(
                alert.rule.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            alert.webhook_sent = True
            alert.save()
            logger.info(f"[ALERTS] Webhook sent for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"[ALERTS] Failed to send webhook for alert {alert.id}: {e}")
    
    def _resolve_alerts_if_needed(self, rule: AlertRule, current_value: float):
        """Resolve active alerts if threshold is no longer exceeded."""
        if not self._threshold_exceeded(rule, current_value):
            active_alerts = Alert.objects.filter(
                rule=rule,
                status='active'
            )
            
            for alert in active_alerts:
                alert.resolve()
                logger.info(f"[ALERTS] Auto-resolved alert {alert.id}")
    
    def get_system_health(self) -> Dict:
        """Get current system health status."""
        return {
            'queue_size': self._get_queue_size(),
            'error_rate': self._get_error_rate(),
            'ffmpeg_available': FFmpegWrapper.check_ffmpeg_available(),
            'disk_usage_percent': self._get_disk_usage_percent(),
            'avg_processing_time': self._get_avg_processing_time(),
            'active_alerts': Alert.objects.filter(status='active').count(),
        }
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(Alert.objects.filter(status='active').select_related('rule'))
    
    def acknowledge_alert(self, alert_id: int, user=None):
        """Acknowledge an alert."""
        try:
            alert = Alert.objects.get(id=alert_id)
            alert.acknowledge(user)
            logger.info(f"[ALERTS] Alert {alert_id} acknowledged by {user}")
            return True
        except Alert.DoesNotExist:
            logger.warning(f"[ALERTS] Alert {alert_id} not found")
            return False
