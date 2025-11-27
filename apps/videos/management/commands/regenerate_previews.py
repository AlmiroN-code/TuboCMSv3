import os

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.videos.models import Video
from apps.videos.models_encoding import MetadataExtractionSettings
from apps.videos.services_encoding import VideoProcessingService


class Command(BaseCommand):
    help = "Regenerate video previews with better quality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--video-id",
            type=int,
            help="Process specific video ID",
        )

    def handle(self, *args, **options):
        video_id = options.get("video_id")

        if video_id:
            videos = Video.objects.filter(id=video_id)
            if not videos.exists():
                self.stdout.write(
                    self.style.ERROR(f"Video with ID {video_id} not found")
                )
                return
        else:
            videos = Video.objects.filter(converted_files__isnull=False).exclude(
                converted_files=[]
            )

        if not videos.exists():
            self.stdout.write(self.style.WARNING("No videos to process"))
            return

        # Get metadata extraction settings
        settings_obj = MetadataExtractionSettings.objects.first()
        if not settings_obj:
            self.stdout.write(self.style.ERROR("No metadata extraction settings found"))
            return

        processed_count = 0
        error_count = 0

        for video in videos:
            self.stdout.write(
                f"\\nRegenerating preview for video: {video.title} (ID: {video.id})"
            )

            try:
                if not video.temp_video_file:
                    self.stdout.write(
                        self.style.WARNING(f"  No temp video file for video {video.id}")
                    )
                    continue

                if not os.path.exists(video.temp_video_file.path):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Temp file does not exist: {video.temp_video_file.path}"
                        )
                    )
                    continue

                # Delete old preview if exists
                if video.preview:
                    try:
                        if os.path.exists(video.preview.path):
                            os.remove(video.preview.path)
                    except:
                        pass
                    video.preview.delete(save=False)

                # Delete old poster if exists
                if video.poster:
                    try:
                        if os.path.exists(video.poster.path):
                            os.remove(video.poster.path)
                    except:
                        pass
                    video.poster.delete(save=False)

                # Regenerate poster and preview
                video_path = video.temp_video_file.path

                # Generate new poster
                poster_filename = f"poster_{video.id}_{os.urandom(8).hex()}.jpeg"
                poster_path = os.path.join(
                    settings.MEDIA_ROOT, "posters", poster_filename
                )
                os.makedirs(os.path.dirname(poster_path), exist_ok=True)

                if VideoProcessingService.extract_poster(
                    video_path, poster_path, settings_obj
                ):
                    video.poster = f"posters/{poster_filename}"
                    self.stdout.write(f"  Generated new poster: {poster_filename}")
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed to generate poster for video {video.id}"
                        )
                    )

                # Generate new preview
                preview_filename = f"preview_{video.id}_{os.urandom(8).hex()}.mp4"
                preview_path = os.path.join(
                    settings.MEDIA_ROOT, "previews", preview_filename
                )
                os.makedirs(os.path.dirname(preview_path), exist_ok=True)

                if VideoProcessingService.extract_preview(
                    video_path, preview_path, settings_obj
                ):
                    video.preview = f"previews/{preview_filename}"
                    self.stdout.write(f"  Generated new preview: {preview_filename}")
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed to generate preview for video {video.id}"
                        )
                    )

                # Save video
                video.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Successfully regenerated preview for video {video.id}"
                    )
                )
                processed_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Error processing video {video.id}: {str(e)}")
                )
                error_count += 1

        self.stdout.write(f"\\nRegeneration complete:")
        self.stdout.write(f"  Successfully processed: {processed_count}")
        self.stdout.write(f"  Errors: {error_count}")
