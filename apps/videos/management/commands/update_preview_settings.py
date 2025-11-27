from django.core.management.base import BaseCommand

from apps.videos.models_encoding import MetadataExtractionSettings


class Command(BaseCommand):
    help = "Update preview settings for better quality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--width",
            type=int,
            default=640,
            help="Preview width (default: 640)",
        )
        parser.add_argument(
            "--height",
            type=int,
            default=360,
            help="Preview height (default: 360)",
        )
        parser.add_argument(
            "--duration",
            type=int,
            default=12,
            help="Preview duration in seconds (default: 12)",
        )
        parser.add_argument(
            "--quality",
            type=int,
            default=18,
            help="Preview quality (lower is better, default: 18)",
        )
        parser.add_argument(
            "--poster-quality",
            type=int,
            default=2,
            help="Poster quality (lower is better, default: 2)",
        )

    def handle(self, *args, **options):
        settings, created = MetadataExtractionSettings.objects.get_or_create(
            is_active=True,
            defaults={
                "poster_width": options["width"],
                "poster_height": options["height"],
                "poster_quality": options["poster_quality"],
                "preview_width": options["width"],
                "preview_height": options["height"],
                "preview_duration": options["duration"],
                "preview_quality": options["quality"],
            },
        )

        if not created:
            settings.poster_width = options["width"]
            settings.poster_height = options["height"]
            settings.poster_quality = options["poster_quality"]
            settings.preview_width = options["width"]
            settings.preview_height = options["height"]
            settings.preview_duration = options["duration"]
            settings.preview_quality = options["quality"]
            settings.save()

        self.stdout.write(self.style.SUCCESS(f"Updated settings:"))
        self.stdout.write(
            f"  Poster: {settings.poster_width}x{settings.poster_height}, quality: {settings.poster_quality}"
        )
        self.stdout.write(
            f"  Preview: {settings.preview_width}x{settings.preview_height}, duration: {settings.preview_duration}s, quality: {settings.preview_quality}"
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Created new settings"))
        else:
            self.stdout.write(self.style.SUCCESS("Updated existing settings"))
