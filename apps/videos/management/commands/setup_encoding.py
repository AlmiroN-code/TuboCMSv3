"""
Django management command to setup default encoding settings.
"""
from django.core.management.base import BaseCommand

from apps.videos.models_encoding import MetadataExtractionSettings, VideoEncodingProfile


class Command(BaseCommand):
    help = "Setup default encoding profiles and metadata extraction settings"

    def handle(self, *args, **options):
        # Create default metadata extraction settings
        settings, created = MetadataExtractionSettings.objects.get_or_create(
            is_active=True,
            defaults={
                "poster_format": "JPEG",
                "poster_width": 250,
                "poster_height": 150,
                "poster_quality": 5,
                "preview_format": "MP4",
                "preview_width": 250,
                "preview_height": 150,
                "preview_quality": 23,
                "preview_duration": 12,
                "preview_segment_duration": 2,
            },
        )

        if created:
            self.stdout.write("Created default metadata extraction settings")
        else:
            self.stdout.write("Metadata extraction settings already exist")

        # Create default encoding profiles
        profiles_data = [
            {
                "name": "360p Mobile",
                "resolution": "360p",
                "bitrate": "800k",
                "width": 640,
                "height": 360,
                "is_active": True,
                "order": 1,
            },
            {
                "name": "720p HD",
                "resolution": "720p",
                "bitrate": "2500k",
                "width": 1280,
                "height": 720,
                "is_active": True,
                "order": 2,
            },
            {
                "name": "1080p Full HD",
                "resolution": "1080p",
                "bitrate": "5000k",
                "width": 1920,
                "height": 1080,
                "is_active": True,
                "order": 3,
            },
        ]

        for profile_data in profiles_data:
            profile, created = VideoEncodingProfile.objects.get_or_create(
                resolution=profile_data["resolution"], defaults=profile_data
            )

            if created:
                self.stdout.write(f"Created profile: {profile_data['name']}")
            else:
                self.stdout.write(f"Profile {profile_data['name']} already exists")

        self.stdout.write(
            self.style.SUCCESS("Successfully setup default encoding settings")
        )
