"""
Service for creating video previews.
"""
import logging
import os
import tempfile
from typing import Optional

from .ffmpeg_wrapper import FFmpegWrapper

logger = logging.getLogger(__name__)


class PreviewService:
    """Service for creating video preview clips."""
    
    def __init__(self, settings=None):
        """
        Initialize preview service.
        
        Args:
            settings: MetadataExtractionSettings instance or None for defaults
        """
        self.settings = settings
        self.width = getattr(settings, 'preview_width', 250)
        self.height = getattr(settings, 'preview_height', 150)
        self.quality = getattr(settings, 'preview_quality', 18)
        self.duration = getattr(settings, 'preview_duration', 12)
        self.segment_duration = getattr(settings, 'preview_segment_duration', 2)
        self.format = getattr(settings, 'preview_format', 'mp4').lower()
    
    def extract(self, video_path: str, output_path: str) -> bool:
        """
        Extract preview from video.
        
        Creates a preview by extracting segments evenly distributed
        across the video and concatenating them.
        
        Args:
            video_path: Path to source video
            output_path: Path for output preview video
            
        Returns:
            bool: True if successful
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        duration = FFmpegWrapper.get_duration(video_path)
        
        if duration <= 0:
            return self._extract_simple(video_path, output_path)
        
        if duration <= self.duration:
            return self._extract_full(video_path, output_path)
        
        # Try complex extraction first, fallback to simple
        if self._extract_segments(video_path, output_path, duration):
            return True
        
        logger.warning("[PREVIEW] Complex extraction failed, trying simple method")
        return self._extract_simple(video_path, output_path)
    
    def _extract_simple(self, video_path: str, output_path: str) -> bool:
        """Extract first N seconds as preview."""
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-t", str(self.duration),
            "-vf", f"scale={self.width}:{self.height}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(self.quality),
            "-profile:v", "high",
            "-level", "4.0",
            "-an",
            "-y", output_path,
        ]
        
        result = FFmpegWrapper.run_command(
            cmd,
            timeout=FFmpegWrapper.DEFAULT_PREVIEW_TIMEOUT,
            operation="preview_simple"
        )
        
        return result.success and os.path.exists(output_path)
    
    def _extract_full(self, video_path: str, output_path: str) -> bool:
        """Extract entire video as preview (for short videos)."""
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"scale={self.width}:{self.height}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(self.quality),
            "-profile:v", "high",
            "-level", "4.0",
            "-an",
            "-y", output_path,
        ]
        
        result = FFmpegWrapper.run_command(
            cmd,
            timeout=FFmpegWrapper.DEFAULT_PREVIEW_TIMEOUT,
            operation="preview_full"
        )
        
        return result.success and os.path.exists(output_path)
    
    def _extract_segments(self, video_path: str, output_path: str, duration: int) -> bool:
        """Extract and concatenate segments from different parts of video."""
        num_segments = self.duration // self.segment_duration
        segment_interval = duration / (num_segments + 1)
        
        segment_files = []
        concat_file = None
        
        try:
            # Create temporary segment files
            for i in range(num_segments):
                start_time = int(segment_interval * (i + 1))
                if start_time + self.segment_duration > duration:
                    start_time = max(0, duration - self.segment_duration)
                
                segment_file = tempfile.NamedTemporaryFile(
                    suffix=".mp4", delete=False
                )
                segment_files.append(segment_file.name)
                segment_file.close()
                
                time_str = self._format_time(start_time)
                
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-ss", time_str,
                    "-t", str(self.segment_duration),
                    "-vf", f"scale={self.width}:{self.height}",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-an",
                    "-y", segment_file.name,
                ]
                
                result = FFmpegWrapper.run_command(
                    cmd,
                    timeout=60,
                    operation=f"preview_segment_{i}"
                )
                
                if not result.success:
                    logger.warning(f"[PREVIEW] Segment {i} extraction failed")
            
            # Create concat file
            concat_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.txt', delete=False
            )
            for seg_file in segment_files:
                if os.path.exists(seg_file) and os.path.getsize(seg_file) > 0:
                    concat_file.write(f"file '{seg_file}'\n")
            concat_file.close()
            
            # Concatenate segments
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file.name,
                "-c", "copy",
                "-y", output_path,
            ]
            
            result = FFmpegWrapper.run_command(
                cmd,
                timeout=60,
                operation="preview_concat"
            )
            
            if result.success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"[PREVIEW] Created: {output_path} ({file_size} bytes)")
                return True
            
            return False
            
        finally:
            # Cleanup temporary files
            for seg_file in segment_files:
                try:
                    if os.path.exists(seg_file):
                        os.unlink(seg_file)
                except:
                    pass
            
            if concat_file:
                try:
                    os.unlink(concat_file.name)
                except:
                    pass
    
    @staticmethod
    def _format_time(seconds: int) -> str:
        """Format seconds to HH:MM:SS."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def cleanup(self, path: str) -> bool:
        """Remove preview file."""
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"[PREVIEW] Cleaned up: {path}")
                return True
        except Exception as e:
            logger.warning(f"[PREVIEW] Cleanup failed for {path}: {e}")
        return False
