"""
Management command to set user processing priority.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Set processing priority for a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username')
        parser.add_argument(
            '--priority',
            type=int,
            default=5,
            help='Priority level (0-10, default: 5)'
        )
        parser.add_argument(
            '--premium',
            action='store_true',
            help='Mark user as premium'
        )
        parser.add_argument(
            '--no-premium',
            action='store_true',
            help='Remove premium status'
        )

    def handle(self, *args, **options):
        username = options['username']
        priority = options['priority']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" not found')
            )
            return
        
        # Update priority
        if 0 <= priority <= 10:
            user.processing_priority = priority
            self.stdout.write(
                self.style.SUCCESS(
                    f'Set priority for {username} to {priority}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR('Priority must be between 0 and 10')
            )
            return
        
        # Update premium status
        if options['premium']:
            user.is_premium = True
            self.stdout.write(
                self.style.SUCCESS(f'Marked {username} as premium')
            )
        elif options['no_premium']:
            user.is_premium = False
            self.stdout.write(
                self.style.SUCCESS(f'Removed premium status from {username}')
            )
        
        user.save()
        
        # Show final priority
        final_priority = user.get_processing_priority()
        self.stdout.write(
            self.style.SUCCESS(
                f'\nFinal processing priority for {username}: {final_priority}'
            )
        )
        self.stdout.write(
            f'  - is_premium: {user.is_premium}'
        )
        self.stdout.write(
            f'  - processing_priority: {user.processing_priority}'
        )
        self.stdout.write(
            f'  - videos_count: {user.videos_count}'
        )
