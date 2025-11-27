"""
Django management command to process videos manually.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.videos.models import Video
from apps.videos.services_encoding import VideoProcessingService


class Command(BaseCommand):
    help = "Process video: extract poster, preview, and encode to profiles"

    def add_arguments(self, parser):
        parser.add_argument("video_id", type=int, help="Video ID to process")
        parser.add_argument(
            "--profiles",
            nargs="+",
            type=int,
            help="Profile IDs to use for encoding (default: all active)",
        )

    def handle(self, *args, **options):
        video_id = options["video_id"]
        profile_ids = options.get("profiles")

        try:
            video = Video.objects.get(id=video_id)
        except Video.DoesNotExist:
            raise CommandError(f"Video with ID {video_id} does not exist")

        if not video.temp_video_file:
            raise CommandError(f"Video {video_id} has no video file to process")

        self.stdout.write(f"Processing video: {video.title} (ID: {video_id})")

        # Process video
        success = VideoProcessingService.process_video(video_id, profile_ids)

        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully processed video {video_id}")
            )
        else:
            raise CommandError(f"Failed to process video {video_id}")
