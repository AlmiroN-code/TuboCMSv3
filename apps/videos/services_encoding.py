"""
Video encoding services for TubeCMS.

This module provides backward compatibility with the old API
while using the new modular services internally.
"""
import logging
import os

from django.conf import settings
from django.core.files import File

from .models import Video, VideoFile
from .models_encoding import MetadataExtractionSettings, VideoEncodingProfile
from .services import (
    ProcessingPipeline, 
    PipelineConfig,
    FFmpegWrapper,
    PosterService,
    PreviewService,
    EncodingService,
    get_suitable_profiles
)

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """
    Legacy service class for backward compatibility.
    
    Delegates to the new modular ProcessingPipeline.
    """

    @staticmethod
    def extract_poster(video_path, output_path, settings_obj):
        """Extract poster from video."""
        service = PosterService(settings_obj)
        return service.extract(video_path, output_path)

    @staticmethod
    def extract_preview(video_path, output_path, settings_obj):
        """Extract preview from video."""
        service = PreviewService(settings_obj)
        return service.extract(video_path, output_path)

    @staticmethod
    def get_video_duration(video_path):
        """Get video duration in seconds."""
        return FFmpegWrapper.get_duration(video_path)

    @staticmethod
    def encode_video(video_path, output_path, profile):
        """Encode video to specific profile."""
        service = EncodingService(os.path.dirname(output_path))
        # Create a minimal profile-like object for single encoding
        result = FFmpegWrapper.run_command(
            [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"scale={profile.width}:{profile.height}",
                "-c:v", "libx264",
                "-preset", "medium",
                "-profile:v", "main",
                "-b:v", f"{profile.bitrate}k",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y", output_path,
            ],
            timeout=FFmpegWrapper.DEFAULT_ENCODE_TIMEOUT,
            operation=f"encode_{profile.resolution}"
        )
        return result.success and os.path.exists(output_path)

    @staticmethod
    def process_video(video_id, selected_profiles=None, progress_callback=None):
        """
        Process video: extract poster, preview, and encode to profiles.
        
        This method maintains backward compatibility while using the new
        modular pipeline internally.
        """
        try:
            video = Video.objects.get(id=video_id)
            if not video.temp_video_file:
                logger.error(f"Video {video_id} has no temp file")
                return False

            # Get video path
            video_path = VideoProcessingService._get_video_path(video)
            if not video_path:
                logger.error(f"Could not find video file for video {video_id}")
                return False

            # Get settings
            settings_obj = MetadataExtractionSettings.objects.filter(
                is_active=True
            ).first()
            if not settings_obj:
                logger.error("No active metadata extraction settings")
                return False

            # Get profiles
            if selected_profiles is None:
                profiles = list(VideoEncodingProfile.objects.filter(is_active=True))
            else:
                profiles = list(VideoEncodingProfile.objects.filter(
                    id__in=selected_profiles, is_active=True
                ))

            if not profiles:
                logger.error("No active profiles found for encoding")
                return False

            # Configure pipeline
            config = PipelineConfig(
                parallel_encoding=True,
                max_parallel_jobs=2,
                cleanup_on_error=True,
                check_disk_space=True
            )

            # Run pipeline
            pipeline = ProcessingPipeline(config)
            result = pipeline.process(
                video_id=video_id,
                video_path=video_path,
                profiles=profiles,
                metadata_settings=settings_obj,
                progress_callback=progress_callback
            )

            if not result.success:
                video.processing_status = "failed"
                video.processing_error = f"{result.error_stage}: {result.error_message}"
                video.save(update_fields=["processing_status", "processing_error"])
                return False

            # Generate HLS/DASH streams if enabled
            VideoProcessingService._generate_streams(video, video_path, profiles, pipeline)

            # Save results to database
            return VideoProcessingService._save_results(video, result, settings_obj)

        except Video.DoesNotExist:
            logger.error(f"Video with id {video_id} not found")
            return False
        except Exception as e:
            logger.exception(f"Error processing video {video_id}")
            VideoProcessingService._handle_error(video_id, str(e))
            return False

    @staticmethod
    def _get_video_path(video):
        """Get the actual path to the video file."""
        if video.temp_video_file:
            try:
                if video.temp_video_file.storage.exists(video.temp_video_file.name):
                    return video.temp_video_file.path
            except:
                pass

        # Fallback: search in tmp directory
        tmp_dir = os.path.join(settings.MEDIA_ROOT, "videos", "tmp")
        if os.path.exists(tmp_dir):
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    if file.endswith(".mp4"):
                        return os.path.join(root, file)
        return None

    @staticmethod
    def _save_results(video, result, settings_obj):
        """Save pipeline results to database."""
        try:
            # Save poster
            if result.poster_path and os.path.exists(result.poster_path):
                poster_filename = os.path.basename(result.poster_path)
                with open(result.poster_path, "rb") as f:
                    video.poster.save(poster_filename, File(f), save=False)
                # Remove temp file after saving to storage
                try:
                    os.remove(result.poster_path)
                except:
                    pass

            # Save preview
            if result.preview_path and os.path.exists(result.preview_path):
                preview_filename = os.path.basename(result.preview_path)
                with open(result.preview_path, "rb") as f:
                    video.preview.save(preview_filename, File(f), save=False)
                try:
                    os.remove(result.preview_path)
                except:
                    pass

            # Clear existing VideoFile records
            VideoFile.objects.filter(video=video).delete()

            # Create VideoFile records for encoded files
            converted_files = []
            video_info = FFmpegWrapper.get_video_info(
                VideoProcessingService._get_video_path(video) or ""
            )
            
            for i, enc_result in enumerate(result.encoded_files):
                if enc_result.success:
                    # Get profile from database
                    try:
                        profile = VideoEncodingProfile.objects.get(
                            resolution=enc_result.resolution
                        )
                    except VideoEncodingProfile.DoesNotExist:
                        continue

                    # Create VideoFile record
                    video_file = VideoFile(
                        video=video,
                        profile=profile,
                        file_size=enc_result.file_size,
                        duration=video_info.get("duration", 0),
                        is_primary=(i == 0),
                    )
                    
                    # Set file path relative to MEDIA_ROOT
                    rel_path = os.path.relpath(
                        enc_result.output_path, 
                        settings.MEDIA_ROOT
                    )
                    video_file.file.name = rel_path
                    video_file.save()

                    converted_files.append(rel_path)

            # Update video metadata
            video.converted_files = converted_files
            video.duration = video_info.get("duration", 0)
            video.resolution = f"{video_info.get('width', 0)}x{video_info.get('height', 0)}"

            # Delete temp file
            VideoProcessingService._cleanup_temp_file(video)

            # Update status
            video.status = "published"
            video.processing_status = "completed"
            video.processing_error = ""
            video.processing_progress = 100

            video.save(update_fields=[
                "poster", "preview", "converted_files", "duration",
                "resolution", "temp_video_file", "status",
                "processing_status", "processing_error", "processing_progress"
            ])

            logger.info(f"Video {video.id} processing completed successfully")
            logger.info(f"Metrics: {result.metrics}")
            return True

        except Exception as e:
            logger.exception(f"Error saving results for video {video.id}")
            return False

    @staticmethod
    def _generate_streams(video, video_path, profiles, pipeline):
        """Generate HLS and DASH streams if enabled in settings."""
        from django.conf import settings as django_settings
        from .models import VideoStream
        
        video_settings = getattr(django_settings, 'VIDEO_PROCESSING', {})
        generate_hls = video_settings.get('GENERATE_HLS', False)
        generate_dash = video_settings.get('GENERATE_DASH', False)
        
        if not generate_hls and not generate_dash:
            return
        
        video_id = video.id
        
        try:
            # Get video duration
            video_info = FFmpegWrapper.get_video_info(video_path)
            duration = video_info.get('duration', 0)
            
            # Generate HLS streams
            if generate_hls:
                logger.info(f"[STREAMS] Generating HLS for video {video_id}")
                hls_results = pipeline.generate_hls_streams(
                    video_id, video_path, profiles
                )
                
                for result in hls_results:
                    if result.get('success'):
                        # Save to VideoStream model
                        profile = next(
                            (p for p in profiles if p.name == result.get('profile')),
                            None
                        )
                        if profile:
                            VideoStream.objects.update_or_create(
                                video=video,
                                stream_type='hls',
                                profile=profile,
                                defaults={
                                    'manifest_path': result.get('playlist_path', ''),
                                    'segment_count': result.get('segment_count', 0),
                                    'total_size': result.get('total_size', 0),
                                    'is_ready': True,
                                }
                            )
                logger.info(f"[STREAMS] HLS generation completed for video {video_id}")
            
            # Generate DASH streams
            if generate_dash:
                logger.info(f"[STREAMS] Generating DASH for video {video_id}")
                dash_results = pipeline.generate_dash_streams(
                    video_id, video_path, profiles, duration
                )
                
                for result in dash_results:
                    if result.get('success'):
                        profile = next(
                            (p for p in profiles if p.name == result.get('profile')),
                            None
                        )
                        if profile:
                            VideoStream.objects.update_or_create(
                                video=video,
                                stream_type='dash',
                                profile=profile,
                                defaults={
                                    'manifest_path': result.get('mpd_path', ''),
                                    'segment_count': result.get('segment_count', 0),
                                    'total_size': result.get('total_size', 0),
                                    'is_ready': True,
                                }
                            )
                logger.info(f"[STREAMS] DASH generation completed for video {video_id}")
                
        except Exception as e:
            logger.warning(f"[STREAMS] Stream generation failed for video {video_id}: {e}")
            # Don't fail the whole process if streaming fails

    @staticmethod
    def _cleanup_temp_file(video):
        """Remove temporary video file."""
        try:
            if video.temp_video_file:
                path = video.temp_video_file.path
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Deleted temp file: {path}")
                video.temp_video_file = None
        except Exception as e:
            logger.warning(f"Error cleaning up temp file: {e}")

    @staticmethod
    def _handle_error(video_id, error_message):
        """Handle processing error."""
        try:
            video = Video.objects.get(id=video_id)
            video.processing_status = "error"
            video.processing_error = error_message
            video.status = "draft"
            video.save(update_fields=[
                "processing_status", "processing_error", "status"
            ])
        except Exception as e:
            logger.error(f"Failed to update error status: {e}")
