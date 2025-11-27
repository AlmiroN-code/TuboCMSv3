"""
Thumbnail generation utilities.
"""
import os
import subprocess

from django.conf import settings
from django.core.files.storage import default_storage


def generate_thumbnail(video_path, output_path, time_offset=10):
    """Generate thumbnail from video using FFmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-ss",
            str(time_offset),
            "-vframes",
            "1",
            "-q:v",
            "2",
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return False


def generate_multiple_thumbnails(video_path, video_id, count=3):
    """Generate multiple thumbnails at different time points."""
    thumbnails = []

    try:
        # Get video duration first
        duration_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            video_path,
        ]

        result = subprocess.run(duration_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])

            # Generate thumbnails at different time points
            time_points = [duration * 0.1, duration * 0.5, duration * 0.9]

            for i, time_point in enumerate(time_points):
                thumbnail_path = os.path.join(
                    settings.MEDIA_ROOT, "thumbnails", f"thumb_{video_id}_{i+1}.jpg"
                )

                if generate_thumbnail(video_path, thumbnail_path, time_point):
                    thumbnails.append(f"thumbnails/thumb_{video_id}_{i+1}.jpg")

        return thumbnails

    except Exception as e:
        print(f"Error generating multiple thumbnails: {e}")
        return []


def optimize_thumbnail(image_path, max_width=320, max_height=180):
    """Optimize thumbnail image size."""
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            # Calculate new size maintaining aspect ratio
            width, height = img.size
            ratio = min(max_width / width, max_height / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)

            # Resize image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save optimized image
            img.save(image_path, "JPEG", quality=85, optimize=True)

        return True

    except Exception as e:
        print(f"Error optimizing thumbnail: {e}")
        return False
