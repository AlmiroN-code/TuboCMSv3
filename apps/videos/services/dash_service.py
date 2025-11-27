"""
Service for DASH (Dynamic Adaptive Streaming over HTTP) generation.

DASH is similar to HLS but uses MP4 segments and XML manifest.
Better for adaptive bitrate streaming with multiple quality levels.
"""
import logging
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .ffmpeg_wrapper import FFmpegWrapper

logger = logging.getLogger(__name__)


class DASHService:
    """Service for generating DASH streams from video files."""
    
    # DASH segment duration in seconds
    DEFAULT_SEGMENT_DURATION = 4
    
    def __init__(self, segment_duration: int = DEFAULT_SEGMENT_DURATION):
        """
        Initialize DASH service.
        
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
        Generate DASH stream from video.
        
        Args:
            video_path: Path to source video
            output_dir: Directory for DASH output
            profile_name: Name of the profile (e.g., "360p")
            width: Video width
            height: Video height
            bitrate: Video bitrate in kbps
            progress_callback: Optional callback for progress
            
        Returns:
            Dict with DASH generation details
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Output paths
        init_segment = os.path.join(output_dir, "init.mp4")
        segment_pattern = os.path.join(output_dir, "segment_%05d.m4s")
        mpd_path = os.path.join(output_dir, "manifest.mpd")
        
        logger.info(f"[DASH] Generating DASH stream for {profile_name}")
        logger.info(f"[DASH] Resolution: {width}x{height}, Bitrate: {bitrate}kbps")
        
        # FFmpeg command for DASH generation
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
            "-f", "dash",
            "-seg_duration", str(self.segment_duration),
            "-init_seg_name", "init.mp4",
            "-media_seg_name", "segment_%05d.m4s",
            "-use_timeline", "1",
            "-use_segmentation", "1",
            "-window_size", "0",  # Keep all segments
            "-y", mpd_path,
        ]
        
        result = FFmpegWrapper.run_command(
            cmd,
            timeout=FFmpegWrapper.DEFAULT_HLS_TIMEOUT,
            operation=f"dash_{profile_name}"
        )
        
        if not result.success:
            logger.error(f"[DASH] Generation failed: {result.error_message}")
            return {
                "success": False,
                "error": result.error_message,
                "profile": profile_name,
            }
        
        # Verify output
        if not os.path.exists(mpd_path):
            error_msg = f"MPD manifest not created: {mpd_path}"
            logger.error(f"[DASH] {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "profile": profile_name,
            }
        
        # Count segments
        segments = [f for f in os.listdir(output_dir) if f.startswith("segment_") and f.endswith(".m4s")]
        total_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in segments)
        
        # Add init segment size
        if os.path.exists(init_segment):
            total_size += os.path.getsize(init_segment)
        
        logger.info(
            f"[DASH] Generated {len(segments)} segments for {profile_name}, "
            f"total size: {total_size // (1024*1024)}MB"
        )
        
        return {
            "success": True,
            "profile": profile_name,
            "mpd_path": mpd_path,
            "segment_count": len(segments),
            "total_size": total_size,
            "duration_seconds": result.duration_seconds,
        }
    
    def generate_master_mpd(
        self,
        dash_outputs: List[Dict[str, Any]],
        output_path: str,
        video_duration: int,
        base_url: str = ""
    ) -> bool:
        """
        Generate master MPD manifest for adaptive bitrate streaming.
        
        Args:
            dash_outputs: List of DASH generation results
            output_path: Path for master MPD
            video_duration: Total video duration in seconds
            base_url: Base URL for stream (e.g., "/media/videos/dash/")
            
        Returns:
            bool: True if successful
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Sort by bitrate (ascending)
            sorted_outputs = sorted(
                [o for o in dash_outputs if o.get("success")],
                key=lambda x: self._extract_bitrate(x.get("profile", "")),
                reverse=True
            )
            
            if not sorted_outputs:
                logger.error("[DASH] No successful DASH outputs for master MPD")
                return False
            
            # Create MPD root element
            mpd = ET.Element("MPD")
            mpd.set("xmlns", "urn:mpeg:dash:schema:mpd:2011")
            mpd.set("minBufferTime", "PT2S")
            mpd.set("type", "static")
            mpd.set("mediaPresentationDuration", self._format_duration(video_duration))
            mpd.set("profiles", "urn:mpeg:dash:profile:isoff-live:2011")
            
            # Period element
            period = ET.SubElement(mpd, "Period")
            period.set("start", "PT0S")
            
            # Add adaptation sets for each quality
            for output in sorted_outputs:
                profile = output.get("profile", "unknown")
                bitrate = self._extract_bitrate(profile)
                width, height = self._extract_resolution_tuple(profile)
                
                # Adaptation set
                adaptation_set = ET.SubElement(period, "AdaptationSet")
                adaptation_set.set("mimeType", "video/mp4")
                adaptation_set.set("segmentAlignment", "true")
                adaptation_set.set("startWithSAP", "1")
                
                # Representation
                representation = ET.SubElement(adaptation_set, "Representation")
                representation.set("id", profile)
                representation.set("bandwidth", str(bitrate * 1000))
                representation.set("width", str(width))
                representation.set("height", str(height))
                
                # Base URL
                base_url_elem = ET.SubElement(representation, "BaseURL")
                mpd_url = f"{base_url}{profile}/manifest.mpd" if base_url else f"{profile}/manifest.mpd"
                base_url_elem.text = mpd_url
                
                # Segment base
                segment_base = ET.SubElement(representation, "SegmentBase")
                segment_base.set("indexRange", "0-0")
                segment_base.set("indexRangeExact", "false")
            
            # Write master MPD
            tree = ET.ElementTree(mpd)
            tree.write(output_path, encoding="utf-8", xml_declaration=True)
            
            logger.info(f"[DASH] Master MPD created: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"[DASH] Failed to create master MPD: {e}")
            return False
    
    @staticmethod
    def _extract_bitrate(profile_name: str) -> int:
        """Extract bitrate from profile name."""
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
        
        return 1000
    
    @staticmethod
    def _extract_resolution_tuple(profile_name: str) -> tuple:
        """Extract resolution as (width, height) tuple."""
        resolution_map = {
            "240p": (426, 240),
            "360p": (640, 360),
            "480p": (854, 480),
            "720p": (1280, 720),
            "1080p": (1920, 1080),
        }
        
        for profile, resolution in resolution_map.items():
            if profile in profile_name:
                return resolution
        
        return (640, 360)
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format duration to ISO 8601 format (PT00H00M00S)."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"PT{hours:02d}H{minutes:02d}M{secs:02d}S"
    
    def cleanup(self, output_dir: str) -> int:
        """
        Remove DASH files.
        
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
                
                logger.info(f"[DASH] Cleaned up {removed} files from {output_dir}")
        except Exception as e:
            logger.warning(f"[DASH] Cleanup failed: {e}")
        
        return removed
