"""
Service for extracting poster/thumbnail from video.
"""
import logging
import os
from typing import Optional

from .ffmpeg_wrapper import FFmpegWrapper

logger = logging.getLogger(__name__)


class PosterService:
    """Service for extracting poster images from videos."""
    
    def __init__(self, settings=None):
        """
        Initialize poster service.
        
        Args:
            settings: MetadataExtractionSettings instance or None for defaults
        """
        self.settings = settings
        self.width = getattr(settings, 'poster_width', 250)
        self.height = getattr(settings, 'poster_height', 150)
        self.quality = getattr(settings, 'poster_quality', 2)
        self.format = getattr(settings, 'poster_format', 'jpg').lower()
    
    def extract(
        self, 
        video_path: str, 
        output_path: str,
        seek_position: Optional[int] = None
    ) -> bool:
        """
        Extract poster from video.
        
        Args:
            video_path: Path to source video
            output_path: Path for output poster image
            seek_position: Position in seconds to extract frame (None = middle)
            
        Returns:
            bool: True if successful
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Get video duration if seek position not specified
        if seek_position is None:
            duration = FFmpegWrapper.get_duration(video_path)
            seek_position = max(1, duration // 2) if duration > 0 else 1
        
        # Format seek time
        time_str = self._format_time(seek_position)
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", time_str,
            "-vframes", "1",
            "-vf", f"scale={self.width}:{self.height}",
            "-f", "image2",
            "-q:v", str(self.quality),
            "-y", output_path,
        ]
        
        result = FFmpegWrapper.run_command(
            cmd,
            timeout=FFmpegWrapper.DEFAULT_POSTER_TIMEOUT,
            operation="poster"
        )
        
        if result.success and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"[POSTER] Created: {output_path} ({file_size} bytes)")
            return True
        
        logger.error(f"[POSTER] Extraction failed: {result.error_message}")
        return False
    
    def extract_multiple(
        self, 
        video_path: str, 
        output_dir: str,
        count: int = 6,
        prefix: str = "thumb"
    ) -> list:
        """
        Extract multiple thumbnails evenly distributed across video.
        
        Args:
            video_path: Path to source video
            output_dir: Directory for output thumbnails
            count: Number of thumbnails to extract
            prefix: Filename prefix
            
        Returns:
            list: Paths to created thumbnails
        """
        os.makedirs(output_dir, exist_ok=True)
        
        duration = FFmpegWrapper.get_duration(video_path)
        if duration <= 0:
            logger.warning("Could not get video duration for multiple thumbnails")
            return []
        
        interval = duration / (count + 1)
        created = []
        
        for i in range(count):
            position = int(interval * (i + 1))
            output_path = os.path.join(output_dir, f"{prefix}_{i+1}.{self.format}")
            
            if self.extract(video_path, output_path, seek_position=position):
                created.append(output_path)
        
        logger.info(f"[POSTER] Created {len(created)}/{count} thumbnails")
        return created
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        """Format seconds to HH:MM:SS."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def cleanup(self, path: str) -> bool:
        """Remove poster file."""
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"[POSTER] Cleaned up: {path}")
                return True
        except Exception as e:
            logger.warning(f"[POSTER] Cleanup failed for {path}: {e}")
        return False
