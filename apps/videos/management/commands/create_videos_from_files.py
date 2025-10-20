from django.core.management.base import BaseCommand
from apps.videos.models import Video
from apps.users.models import User
from apps.core.models import Category
from django.core.files import File
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Create videos from files in tmp directory'

    def handle(self, *args, **options):
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # Get or create category
        category, created = Category.objects.get_or_create(
            name='Test',
            defaults={'description': 'Test category'}
        )
        
        # Get files from tmp directory
        tmp_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'tmp')
        video_files = []
        
        for filename in os.listdir(tmp_dir):
            if filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                file_path = os.path.join(tmp_dir, filename)
                if os.path.isfile(file_path):
                    video_files.append((filename, file_path))
        
        self.stdout.write(f'Found {len(video_files)} video files')
        
        created_count = 0
        
        for filename, file_path in video_files:
            # Create video title from filename
            title = os.path.splitext(filename)[0].replace('_', ' ').title()
            
            # Check if video already exists
            if Video.objects.filter(title=title).exists():
                self.stdout.write(f'Video "{title}" already exists, skipping')
                continue
            
            try:
                # Create video object
                video = Video.objects.create(
                    title=title,
                    description=f'Test video created from {filename}',
                    user=admin_user,
                    category=category,
                    status='published',
                    is_published=True
                )
                
                # Set temp video file
                with open(file_path, 'rb') as f:
                    video.temp_video_file.save(filename, File(f), save=True)
                
                self.stdout.write(self.style.SUCCESS(f'Created video: {title} (ID: {video.id})'))
                created_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating video from {filename}: {str(e)}'))
        
        self.stdout.write(f'\\nCreated {created_count} videos')









