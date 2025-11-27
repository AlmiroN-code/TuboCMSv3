"""
Service for HLS (HTTP Live Streaming) generation.

HLS breaks video into small segments (~10s each) with a playlist manifest.
This enables adaptive bitrate streaming and better user experience.
"""
import logging
import os
import subprocess
from typing import Optional, Dict, Any

from .ffmpeg_wrapper import FFmpegWrapper

logger = logging.getLogger(__name__)


class HLSService:
    """Service for generating HLS streams from video files."""
    
    # HLS segment duration in seconds
    DEFAULT_SEGMENT_DURATION = 10
    
    # Number of segments to keep in playlist
    DEFAULT_PLAYLIST_SIZE = 3
    
    def __init__(self, segment_duration: int = DEFAULT_SEGMENT_DURATION):
        """
        Initialize HLS service.
        
        Args:
            segment_duration: Duration of each segment in seconds
        """
        self.segment_duration = segment_duration
    
    def generate(
        self,
        video_path: str,
        output_dir: str,
        profile_name: str,
        width: int,
        height: int,
        bitrate: int,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate HLS stream from video.
        
        Args:
            video_path: Path to source video
            output_dir: Directory for HLS output
            profile_name: Name of the profile (e.g., "360p")
            width: Video width
            height: Video height
            bitrate: Video bitrate in kbps
            progress_callback: Optional callback for progress
            
        Returns:
            Dict with HLS generation details
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Output paths
        playlist_path = os.path.join(output_dir, "playlist.m3u8")
        segment_pattern = os.path.join(output_dir, "segment_%03d.ts")
        
        logger.info(f"[HLS] Generating HLS stream for {profile_name}")
        logger.info(f"[HLS] Resolution: {width}x{height}, Bitrate: {bitrate}kbps")
        
        # FFmpeg command for HLS generation
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"scale={width}:{height}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-profile:v", "main",
            "-b:v", f"{bitrate}k",
            "-c:a", "aac",
            "-b:a", "128k",
            "-hls_time", str(self.segment_duration),
            "-hls_playlist_type", "vod",  # Video on Demand
            "-hls_segment_filename", segment_pattern,
            "-y", playlist_path,
        ]
        
        result = FFmpegWrapper.run_command(
            cmd,
            timeout=FFmpegWrapper.DEFAULT_HLS_TIMEOUT,
            operation=f"hls_{profile_name}"
        )
        
        if not result.success:
            logger.error(f"[HLS] Generation failed: {result.error_message}")
            return {
                "success": False,
                "error": result.error_message,
                "profile": profile_name,
            }
        
        # Verify output
        if not os.path.exists(playlist_path):
            error_msg = f"Playlist not created: {playlist_path}"
            logger.error(f"[HLS] {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "profile": profile_name,
            }
        
        # Count segments
        segments = [f for f in os.listdir(output_dir) if f.startswith("segment_") and f.endswith(".ts")]
        total_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in segments)
        
        logger.info(
            f"[HLS] Generated {len(segments)} segments for {profile_name}, "
            f"total size: {total_size // (1024*1024)}MB"
        )
        
        return {
            "success": True,
            "profile": profile_name,
            "playlist_path": playlist_path,
            "segment_count": len(segments),
            "total_size": total_size,
            "duration_seconds": result.duration_seconds,
        }
    
    def generate_master_playlist(
        self,
        hls_outputs: list,
        output_path: str,
        base_url: str = ""
    ) -> bool:
        """
        Generate master playlist for adaptive bitrate streaming.
        
        Master playlist references multiple quality variants.
        
        Args:
            hls_outputs: List of HLS generation results
            output_path: Path for master playlist
            base_url: Base URL for stream (e.g., "/media/videos/hls/")
            
        Returns:
            bool: True if successful
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Sort by bitrate (ascending)
            sorted_outputs = sorted(
                [o for o in hls_outputs if o.get("success")],
                key=lambda x: self._extract_bitrate(x.get("profile", "")),
                reverse=True
            )
            
            if not sorted_outputs:
                logger.error("[HLS] No successful HLS outputs for master playlist")
                return False
            
            # Build master playlist
            lines = [
                "#EXTM3U",
                "#EXT-X-VERSION:3",
                "#EXT-X-TARGETDURATION:10",
                "#EXT-X-MEDIA-SEQUENCE:0",
            ]
            
            for output in sorted_outputs:
                profile = output.get("profile", "unknown")
                bitrate = self._extract_bitrate(profile)
                
                # Extract resolution from profile name (e.g., "360p" -> 360)
                resolution = self._extract_resolution(profile)
                
                # Playlist URL
                playlist_url = f"{base_url}{profile}/playlist.m3u8" if base_url else f"{profile}/playlist.m3u8"
                
                # Add variant stream
                lines.append(f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate * 1000},RESOLUTION={resolution}")
                lines.append(playlist_url)
            
            # Write master playlist
            with open(output_path, "w") as f:
                f.write("\n".join(lines) + "\n")
            
            logger.info(f"[HLS] Master playlist created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[HLS] Failed to create master playlist: {e}")
            return False
    
    @staticmethod
    def _extract_bitrate(profile_name: str) -> int:
        """Extract bitrate from profile name (e.g., "360p" -> 500)."""
        # Map common profiles to bitrates
        bitrate_map = {
            "240p": 300,
            "360p": 500,
            "480p": 1000,
            "720p": 2500,
            "1080p": 5000,
        }
        
        for profile, bitrate in bitrate_map.items():
            if profile in profile_name:
                return bitrate
        
        return 1000  # Default
    
    @staticmethod
    def _extract_resolution(profile_name: str) -> str:
        """Extract resolution from profile name (e.g., "360p" -> "640x360")."""
        resolution_map = {
            "240p": "426x240",
            "360p": "640x360",
            "480p": "854x480",
            "720p": "1280x720",
            "1080p": "1920x1080",
        }
        
        for profile, resolution in resolution_map.items():
            if profile in profile_name:
                return resolution
        
        return "640x360"  # Default
    
    def cleanup(self, output_dir: str) -> int:
        """
        Remove HLS files.
        
        Returns:
            Number of files removed
        """
        removed = 0
        try:
            if os.path.exists(output_dir):
                for file in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        removed += 1
                
                # Remove directory if empty
                if not os.listdir(output_dir):
                    os.rmdir(output_dir)
                
                logger.info(f"[HLS] Cleaned up {removed} files from {output_dir}")
        except Exception as e:
            logger.warning(f"[HLS] Cleanup failed: {e}")
        
        return removed
