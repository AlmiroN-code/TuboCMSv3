"""
FFmpeg wrapper with timeouts, logging, and error handling.
"""
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class FFmpegResult:
    """Result of FFmpeg command execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    error_message: str = ""
    timed_out: bool = False
    duration_seconds: float = 0.0


class FFmpegWrapper:
    """Wrapper for FFmpeg commands with timeouts and logging."""
    
    # Default timeouts in seconds
    DEFAULT_PROBE_TIMEOUT = 30
    DEFAULT_POSTER_TIMEOUT = 60
    DEFAULT_PREVIEW_TIMEOUT = 300  # 5 minutes
    DEFAULT_ENCODE_TIMEOUT = 3600  # 1 hour per profile
    DEFAULT_HLS_TIMEOUT = 7200  # 2 hours for HLS
    
    # Minimum free disk space in bytes (1GB)
    MIN_FREE_DISK_SPACE = 1024 * 1024 * 1024
    
    @classmethod
    def check_ffmpeg_available(cls) -> bool:
        """Check if FFmpeg is available."""
        result = cls.run_command(
            ["ffmpeg", "-version"],
            timeout=10,
            operation="version_check"
        )
        return result.success
    
    @classmethod
    def check_disk_space(cls, path: str, required_bytes: int = None) -> tuple:
        """
        Check available disk space.
        
        Returns:
            tuple: (has_space: bool, free_bytes: int, message: str)
        """
        try:
            if os.path.isfile(path):
                path = os.path.dirname(path)
            
            total, used, free = shutil.disk_usage(path)
            required = required_bytes or cls.MIN_FREE_DISK_SPACE
            
            if free < required:
                return (
                    False, 
                    free, 
                    f"Insufficient disk space: {free // (1024*1024)}MB free, "
                    f"{required // (1024*1024)}MB required"
                )
            return (True, free, f"Disk space OK: {free // (1024*1024)}MB free")
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return (True, 0, "Could not check disk space")
    
    @staticmethod
    def run_command(
        cmd: list,
        timeout: Optional[int] = None,
        operation: str = "ffmpeg"
    ) -> FFmpegResult:
        """
        Run FFmpeg command with timeout and structured logging.
        """
        import time
        start_time = time.time()
        cmd_str = " ".join(cmd)
        logger.info(f"[{operation.upper()}] Starting: {cmd_str[:200]}...")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                logger.info(f"[{operation.upper()}] Success in {duration:.2f}s")
                return FFmpegResult(
                    success=True,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode,
                    duration_seconds=duration
                )
            else:
                error_msg = f"FFmpeg failed with code {result.returncode}: {result.stderr[:500]}"
                logger.error(f"[{operation.upper()}] {error_msg}")
                return FFmpegResult(
                    success=False,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    return_code=result.returncode,
                    error_message=error_msg,
                    duration_seconds=duration
                )
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            error_msg = f"Command timed out after {timeout} seconds"
            logger.error(f"[{operation.upper()}] {error_msg}")
            return FFmpegResult(
                success=False,
                error_message=error_msg,
                timed_out=True,
                duration_seconds=duration
            )
            
        except FileNotFoundError:
            error_msg = "FFmpeg not found. Please install FFmpeg and add to PATH."
            logger.error(f"[{operation.upper()}] {error_msg}")
            return FFmpegResult(
                success=False,
                error_message=error_msg
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(f"[{operation.upper()}] {error_msg}")
            return FFmpegResult(
                success=False,
                error_message=error_msg,
                duration_seconds=duration
            )
    
    @classmethod
    def get_video_info(cls, video_path: str) -> Dict[str, Any]:
        """
        Get video metadata using ffprobe.
        
        Returns dict with: duration, width, height, bitrate, codec, fps, file_size
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        result = cls.run_command(
            cmd,
            timeout=cls.DEFAULT_PROBE_TIMEOUT,
            operation="probe"
        )
        
        if not result.success:
            logger.warning(f"Failed to get video info: {result.error_message}")
            return {}
        
        try:
            data = json.loads(result.stdout)
            
            # Extract video stream info
            video_stream = None
            audio_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video" and not video_stream:
                    video_stream = stream
                elif stream.get("codec_type") == "audio" and not audio_stream:
                    audio_stream = stream
            
            if not video_stream:
                return {}
            
            format_info = data.get("format", {})
            
            return {
                "duration": int(float(format_info.get("duration", 0))),
                "width": video_stream.get("width", 0),
                "height": video_stream.get("height", 0),
                "bitrate": int(format_info.get("bit_rate", 0)) // 1000,
                "codec": video_stream.get("codec_name", ""),
                "fps": cls._parse_fps(video_stream.get("r_frame_rate", "0/1")),
                "file_size": int(format_info.get("size", 0)),
                "has_audio": audio_stream is not None,
                "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse video info: {e}")
            return {}
    
    @staticmethod
    def _parse_fps(fps_str: str) -> float:
        """Parse FPS from ffprobe format (e.g., '30/1' or '29.97')."""
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return round(float(num) / float(den), 2)
            return round(float(fps_str), 2)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    @classmethod
    def get_duration(cls, video_path: str) -> int:
        """Get video duration in seconds."""
        info = cls.get_video_info(video_path)
        return info.get("duration", 0)
    
    @classmethod
    def get_resolution(cls, video_path: str) -> tuple:
        """Get video resolution as (width, height)."""
        info = cls.get_video_info(video_path)
        return (info.get("width", 0), info.get("height", 0))


def get_suitable_profiles(video_path: str, profiles) -> list:
    """
    Filter encoding profiles based on source video quality.
    Don't upscale - only encode to equal or lower resolutions.
    """
    source_width, source_height = FFmpegWrapper.get_resolution(video_path)
    
    if source_width == 0 or source_height == 0:
        logger.warning("Could not determine source resolution, using all profiles")
        return list(profiles)
    
    logger.info(f"Source resolution: {source_width}x{source_height}")
    
    suitable = []
    for profile in profiles:
        if profile.height <= source_height:
            suitable.append(profile)
            logger.info(f"Profile {profile.name} ({profile.resolution}) - suitable")
        else:
            logger.info(f"Profile {profile.name} ({profile.resolution}) - skipped (upscale)")
    
    if not suitable:
        lowest = min(profiles, key=lambda p: p.height)
        suitable.append(lowest)
        logger.warning(f"No suitable profiles, using lowest: {lowest.name}")
    
    return suitable
