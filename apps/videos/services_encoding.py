"""
Video encoding services for TubeCMS.
"""
import os
import subprocess
import tempfile
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from .models import Video, VideoFile
from .models_encoding import VideoEncodingProfile, MetadataExtractionSettings


class VideoProcessingService:
    """Service for video processing and encoding."""
    
    @staticmethod
    def extract_poster(video_path, output_path, settings_obj):
        """Extract poster from video."""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', '00:00:01',  # Extract from 1 second
                '-vframes', '1',
                '-vf', f'scale={settings_obj.poster_width}:{settings_obj.poster_height}',  # Use settings from admin
                '-f', 'image2',
                '-q:v', str(settings_obj.poster_quality),  # Use quality from settings
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                return True
            else:
                print(f"Poster extraction failed: {result.stderr}")
                return False
            
        except Exception as e:
            print(f"Error extracting poster: {e}")
            return False

    @staticmethod
    def extract_preview(video_path, output_path, settings_obj):
        """Extract video preview."""
        try:
            # Use settings from admin
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-t', str(settings_obj.preview_duration),  # Use duration from settings
                '-vf', f'scale={settings_obj.preview_width}:{settings_obj.preview_height}',  # Use size from settings
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', str(settings_obj.preview_quality),  # Use quality from settings
                '-profile:v', 'high',
                '-level', '4.0',
                '-an',  # No audio
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                return True
            else:
                print(f"Preview extraction failed: {result.stderr}")
                return False
            
        except Exception as e:
            print(f"Error extracting preview: {e}")
            return False

    @staticmethod
    def get_video_duration(video_path):
        """Get video duration in seconds."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return int(float(result.stdout.strip()))
            return 0
            
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return 0

    @staticmethod
    def encode_video(video_path, output_path, profile):
        """Encode video to specific profile."""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'scale={profile.width}:{profile.height}',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-profile:v', 'main',  # Use main profile instead of high
                '-b:v', f'{profile.bitrate}k',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error encoding video: {e}")
            return False

    @staticmethod
    def process_video(video_id, selected_profiles=None):
        """Process video: extract poster, preview, and encode to profiles."""
        try:
            video = Video.objects.get(id=video_id)
            if not video.temp_video_file:
                return False
            
            # Use video ID as slug if not exists
            if not video.slug:
                video.slug = f"video-{video.id}"
                video.save(update_fields=['slug'])
            
            # Get settings
            settings_obj = MetadataExtractionSettings.objects.filter(is_active=True).first()
            if not settings_obj:
                return False
            
            # Get active profiles
            if selected_profiles is None:
                profiles = VideoEncodingProfile.objects.filter(is_active=True)
            else:
                profiles = VideoEncodingProfile.objects.filter(id__in=selected_profiles, is_active=True)
            
            if not profiles.exists():
                print("No active profiles found for encoding")
                return False
            
            # Use original file from tmp directory
            # Find the original file in tmp directory
            tmp_dir = os.path.join(settings.MEDIA_ROOT, 'videos', 'tmp')
            
            # Check if temp_video_file exists and is accessible
            if video.temp_video_file and video.temp_video_file.storage.exists(video.temp_video_file.name):
                video_path = video.temp_video_file.path
            else:
                # Fallback: search for any mp4 file in tmp directory
                original_files = []
                for root, dirs, files in os.walk(tmp_dir):
                    for file in files:
                        if file.endswith('.mp4'):
                            original_files.append(os.path.join(root, file))
                
                if original_files:
                    video_path = original_files[0]  # Use first found file
                else:
                    print(f"No video files found in {tmp_dir}")
                    return False
            
            # Extract poster
            poster_filename = f"poster_{video.id}.{settings_obj.poster_format.lower()}"
            poster_path = os.path.join(settings.MEDIA_ROOT, 'posters', poster_filename)
            os.makedirs(os.path.dirname(poster_path), exist_ok=True)
            
            if VideoProcessingService.extract_poster(video_path, poster_path, settings_obj):
                with open(poster_path, 'rb') as f:
                    video.poster.save(poster_filename, File(f), save=True)
                os.remove(poster_path)
            
            # Extract preview
            preview_filename = f"preview_{video.id}.{settings_obj.preview_format.lower()}"
            preview_path = os.path.join(settings.MEDIA_ROOT, 'previews', preview_filename)
            os.makedirs(os.path.dirname(preview_path), exist_ok=True)
            
            if VideoProcessingService.extract_preview(video_path, preview_path, settings_obj):
                with open(preview_path, 'rb') as f:
                    video.preview.save(preview_filename, File(f), save=True)
                os.remove(preview_path)
            
            # Get video duration
            duration = VideoProcessingService.get_video_duration(video_path)
            video.duration = duration
            video.save()
            
            # Clear existing VideoFile records to prevent duplicates
            VideoFile.objects.filter(video=video).delete()
            
            # Encode to profiles
            converted_files = []
            for profile in profiles:
                output_filename = f"{video.id}_{profile.resolution}.mp4"
                output_dir = os.path.join(settings.MEDIA_ROOT, 'videos', profile.resolution)
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_filename)
                
                if VideoProcessingService.encode_video(video_path, output_path, profile):
                    # Create VideoFile record
                    video_file = VideoFile.objects.create(
                        video=video,
                        profile=profile,
                        file=f"videos/{profile.resolution}/{output_filename}",
                        file_size=os.path.getsize(output_path),
                        duration=duration,
                        is_primary=(profile == profiles.first())  # First profile is primary
                    )
                    
                    # Add to converted files list
                    converted_files.append(f"videos/{profile.resolution}/{output_filename}")
            
            # Update video with converted files
            video.converted_files = converted_files
            # Don't replace temp_video_file - keep original for reference
            
            # Keep temporary file for reference - don't delete it
            # This allows for re-processing if needed
            print(f"Processing completed for video {video.id}")
            print(f"Converted files: {converted_files}")
            print(f"Poster created: {bool(video.poster)}")
            print(f"Preview created: {bool(video.preview)}")
            
            # Debug: Check if files were actually created
            if converted_files:
                for file_path in converted_files:
                    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                    print(f"Checking file: {full_path} - exists: {os.path.exists(full_path)}")
            
            # Debug: Check if original file still exists
            print(f"Original file path: {video_path}")
            print(f"Original file exists: {os.path.exists(video_path)}")
            
            # Debug: Check if temp_video_file exists
            if video.temp_video_file:
                print(f"Temp video file: {video.temp_video_file}")
                print(f"Temp video file exists: {video.temp_video_file.storage.exists(video.temp_video_file.name)}")
            
            video.processing_status = 'completed'
            video.save()
            
            return True
            
        except Exception as e:
            print(f"Error processing video: {e}")
            video.processing_status = 'failed'
            video.processing_error = str(e)
            video.save()
            return False
