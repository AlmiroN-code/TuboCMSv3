import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.videos.models import Video
from apps.videos.models_encoding import VideoEncodingProfile
from apps.videos.services_encoding import VideoProcessingService


class Command(BaseCommand):
    help = "Process all videos for encoding"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force reprocessing of already processed videos",
        )

    def handle(self, *args, **options):
        force = options["force"]

        # Get all videos
        if force:
            videos = Video.objects.all()
            self.stdout.write(f"Processing all {videos.count()} videos (force mode)")
        else:
            videos = Video.objects.filter(
                converted_files__isnull=True
            ) | Video.objects.filter(converted_files=[])
            self.stdout.write(f"Processing {videos.count()} unprocessed videos")

        if not videos.exists():
            self.stdout.write(self.style.WARNING("No videos to process"))
            return

        # Get active encoding profiles
        profiles = VideoEncodingProfile.objects.filter(is_active=True)
        if not profiles.exists():
            self.stdout.write(self.style.ERROR("No active encoding profiles found"))
            return

        self.stdout.write(
            f'Using {profiles.count()} encoding profiles: {list(profiles.values_list("name", flat=True))}'
        )

        processed_count = 0
        error_count = 0

        for video in videos:
            self.stdout.write(f"\\nProcessing video: {video.title} (ID: {video.id})")

            try:
                # Check if video has temp file
                if not video.temp_video_file:
                    self.stdout.write(
                        self.style.WARNING(f"  No temp video file for video {video.id}")
                    )
                    continue

                # Check if temp file exists
                if not os.path.exists(video.temp_video_file.path):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Temp file does not exist: {video.temp_video_file.path}"
                        )
                    )
                    continue

                # Process the video
                profile_ids = list(profiles.values_list("id", flat=True))
                success = VideoProcessingService.process_video(video.id, profile_ids)

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f"  Successfully processed video {video.id}")
                    )
                    processed_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"  Failed to process video {video.id}")
                    )
                    error_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Error processing video {video.id}: {str(e)}")
                )
                error_count += 1

        self.stdout.write(f"\\nProcessing complete:")
        self.stdout.write(f"  Successfully processed: {processed_count}")
        self.stdout.write(f"  Errors: {error_count}")
