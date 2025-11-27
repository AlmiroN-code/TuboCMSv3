"""
Management command to create default alert rules.
"""
from django.core.management.base import BaseCommand
from apps.videos.models_alerts import AlertRule


class Command(BaseCommand):
    help = 'Create default alert rules for system monitoring'

    def handle(self, *args, **options):
        self.stdout.write('Creating default alert rules...')
        
        rules = [
            {
                'name': 'High Queue Size',
                'alert_type': 'queue_size',
                'threshold_value': 50.0,
                'severity': 'warning',
                'check_interval_minutes': 5,
                'cooldown_minutes': 30,
                'send_email': True,
            },
            {
                'name': 'Critical Queue Size',
                'alert_type': 'queue_size',
                'threshold_value': 100.0,
                'severity': 'critical',
                'check_interval_minutes': 5,
                'cooldown_minutes': 15,
                'send_email': True,
            },
            {
                'name': 'High Error Rate',
                'alert_type': 'error_rate',
                'threshold_value': 20.0,  # 20% errors
                'severity': 'error',
                'check_interval_minutes': 10,
                'cooldown_minutes': 60,
                'send_email': True,
            },
            {
                'name': 'FFmpeg Unavailable',
                'alert_type': 'ffmpeg_unavailable',
                'threshold_value': 0.5,
                'severity': 'critical',
                'check_interval_minutes': 5,
                'cooldown_minutes': 30,
                'send_email': True,
            },
            {
                'name': 'Low Disk Space',
                'alert_type': 'disk_space',
                'threshold_value': 85.0,  # 85% usage
                'severity': 'warning',
                'check_interval_minutes': 15,
                'cooldown_minutes': 120,
                'send_email': True,
            },
            {
                'name': 'Critical Disk Space',
                'alert_type': 'disk_space',
                'threshold_value': 95.0,  # 95% usage
                'severity': 'critical',
                'check_interval_minutes': 5,
                'cooldown_minutes': 30,
                'send_email': True,
            },
            {
                'name': 'High Processing Time',
                'alert_type': 'processing_time',
                'threshold_value': 30.0,  # 30 minutes average
                'severity': 'warning',
                'check_interval_minutes': 30,
                'cooldown_minutes': 120,
                'send_email': True,
            },
        ]
        
        created = 0
        skipped = 0
        
        for rule_data in rules:
            rule, created_flag = AlertRule.objects.get_or_create(
                name=rule_data['name'],
                alert_type=rule_data['alert_type'],
                defaults=rule_data
            )
            
            if created_flag:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {rule.name}')
                )
            else:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f'- Skipped (exists): {rule.name}')
                )
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done! Created {created} rules, skipped {skipped} existing rules.'
            )
        )
        self.stdout.write('')
        self.stdout.write('Configure email recipients in admin panel: /admin/videos/alertrule/')
