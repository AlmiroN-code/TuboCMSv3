"""
Models for video processing alerts and monitoring.
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta

from apps.core.models import TimeStampedModel


class AlertRule(TimeStampedModel):
    """Configuration for alert rules."""
    
    ALERT_TYPE_CHOICES = [
        ('queue_size', 'Queue Size'),
        ('error_rate', 'Error Rate'),
        ('ffmpeg_unavailable', 'FFmpeg Unavailable'),
        ('disk_space', 'Disk Space Low'),
        ('processing_time', 'Processing Time High'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text="Human-readable name for the alert rule"
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPE_CHOICES,
        help_text="Type of condition to monitor"
    )
    threshold_value = models.FloatField(
        help_text="Threshold value that triggers the alert"
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default='warning'
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this alert rule is active"
    )
    check_interval_minutes = models.PositiveIntegerField(
        default=5,
        help_text="How often to check this condition (in minutes)"
    )
    cooldown_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minimum time between alerts of the same type"
    )
    
    # Notification settings
    send_email = models.BooleanField(
        default=True,
        help_text="Send email notifications"
    )
    email_recipients = models.TextField(
        blank=True,
        help_text="Comma-separated list of email addresses"
    )
    webhook_url = models.URLField(
        blank=True,
        help_text="Webhook URL for notifications (Slack, Discord, etc.)"
    )
    
    class Meta:
        verbose_name = "Alert Rule"
        verbose_name_plural = "Alert Rules"
        unique_together = ['alert_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_alert_type_display()})"
    
    def get_email_list(self):
        """Get list of email recipients."""
        if not self.email_recipients:
            return []
        return [email.strip() for email in self.email_recipients.split(',') if email.strip()]


class Alert(TimeStampedModel):
    """Individual alert instances."""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('acknowledged', 'Acknowledged'),
    ]
    
    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active'
    )
    message = models.TextField(
        help_text="Alert message with details"
    )
    current_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Current value that triggered the alert"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional alert metadata"
    )
    
    # Notification tracking
    email_sent = models.BooleanField(default=False)
    webhook_sent = models.BooleanField(default=False)
    
    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(
        max_length=100,
        blank=True,
        help_text="Who acknowledged the alert"
    )
    
    class Meta:
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['rule', 'status']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} - {self.get_status_display()}"
    
    def acknowledge(self, user=None):
        """Mark alert as acknowledged."""
        self.status = 'acknowledged'
        self.acknowledged_at = timezone.now()
        if user:
            self.acknowledged_by = str(user)
        self.save()
    
    def resolve(self):
        """Mark alert as resolved."""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()
    
    @property
    def age_minutes(self):
        """Get alert age in minutes."""
        return int((timezone.now() - self.created_at).total_seconds() / 60)


class SystemMetric(TimeStampedModel):
    """System metrics for monitoring."""
    
    METRIC_TYPE_CHOICES = [
        ('queue_length', 'Queue Length'),
        ('active_tasks', 'Active Tasks'),
        ('error_count', 'Error Count'),
        ('processing_time_avg', 'Average Processing Time'),
        ('disk_usage', 'Disk Usage'),
        ('ffmpeg_status', 'FFmpeg Status'),
    ]
    
    metric_type = models.CharField(
        max_length=30,
        choices=METRIC_TYPE_CHOICES
    )
    value = models.FloatField(
        help_text="Metric value"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metric data"
    )
    
    class Meta:
        verbose_name = "System Metric"
        verbose_name_plural = "System Metrics"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['metric_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value}"
    
    @classmethod
    def record(cls, metric_type, value, metadata=None):
        """Record a new metric value."""
        return cls.objects.create(
            metric_type=metric_type,
            value=value,
            metadata=metadata or {}
        )
    
    @classmethod
    def get_latest(cls, metric_type):
        """Get latest value for a metric type."""
        try:
            return cls.objects.filter(metric_type=metric_type).latest('created_at')
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_average(cls, metric_type, hours=24):
        """Get average value over time period."""
        since = timezone.now() - timedelta(hours=hours)
        metrics = cls.objects.filter(
            metric_type=metric_type,
            created_at__gte=since
        )
        if metrics.exists():
            return metrics.aggregate(avg=models.Avg('value'))['avg']
        return None
