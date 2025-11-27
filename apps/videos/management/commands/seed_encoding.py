from django.core.management.base import BaseCommand

from apps.videos.models_encoding import MetadataExtractionSettings, VideoEncodingProfile


class Command(BaseCommand):
    help = (
        "Seed metadata extraction settings and encoding profiles for video processing"
    )

    def handle(self, *args, **options):
        if not MetadataExtractionSettings.objects.filter(is_active=True).exists():
            MetadataExtractionSettings.objects.create(is_active=True)
            self.stdout.write(
                self.style.SUCCESS("Created active MetadataExtractionSettings")
            )
        else:
            self.stdout.write("Active MetadataExtractionSettings already exists")

        if not VideoEncodingProfile.objects.exists():
            VideoEncodingProfile.objects.create(
                name="360p",
                resolution="360p",
                width=640,
                height=360,
                bitrate=800,
                order=1,
            )
            VideoEncodingProfile.objects.create(
                name="720p",
                resolution="720p",
                width=1280,
                height=720,
                bitrate=2500,
                order=2,
            )
            self.stdout.write(
                self.style.SUCCESS("Created default encoding profiles (360p, 720p)")
            )
        else:
            self.stdout.write("Encoding profiles already exist")

        self.stdout.write(self.style.SUCCESS("Seeding complete"))
