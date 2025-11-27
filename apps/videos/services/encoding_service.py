"""
Service for video encoding to different profiles.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any

from .ffmpeg_wrapper import FFmpegWrapper, get_suitable_profiles

logger = logging.getLogger(__name__)


@dataclass
class EncodingResult:
    """Result of encoding a single profile."""
    profile_name: str
    resolution: str
    success: bool
    output_path: str = ""
    file_size: int = 0
    duration_seconds: float = 0.0
    error_message: str = ""


class EncodingService:
    """Service for encoding videos to different quality profiles."""
    
    # Maximum parallel encoding jobs
    MAX_PARALLEL_JOBS = 2
    
    def __init__(self, output_dir: str):
        """
        Initialize encoding service.
        
        Args:
            output_dir: Base directory for encoded files
        """
        self.output_dir = output_dir
    
    def encode_single(
        self, 
        video_path: str, 
        profile,
        video_id: int,
        progress_callback: Optional[Callable] = None
    ) -> EncodingResult:
        """
        Encode video to a single profile.
        
        Args:
            video_path: Path to source video
            profile: VideoEncodingProfile instance
            video_id: Video ID for filename
            progress_callback: Optional callback for progress updates
            
        Returns:
            EncodingResult with encoding details
        """
        output_filename = f"{video_id}_{profile.resolution}.mp4"
        output_dir = os.path.join(self.output_dir, profile.resolution)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        logger.info(f"[ENCODE] Starting {profile.resolution} for video {video_id}")
        
        cmd = [
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
        ]
        
        result = FFmpegWrapper.run_command(
            cmd,
            timeout=FFmpegWrapper.DEFAULT_ENCODE_TIMEOUT,
            operation=f"encode_{profile.resolution}"
        )
        
        if result.success and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(
                f"[ENCODE] Completed {profile.resolution}: "
                f"{file_size // (1024*1024)}MB in {result.duration_seconds:.1f}s"
            )
            return EncodingResult(
                profile_name=profile.name,
                resolution=profile.resolution,
                success=True,
                output_path=output_path,
                file_size=file_size,
                duration_seconds=result.duration_seconds
            )
        
        logger.error(f"[ENCODE] Failed {profile.resolution}: {result.error_message}")
        return EncodingResult(
            profile_name=profile.name,
            resolution=profile.resolution,
            success=False,
            error_message=result.error_message,
            duration_seconds=result.duration_seconds
        )
    
    def encode_multiple(
        self,
        video_path: str,
        profiles: list,
        video_id: int,
        parallel: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> List[EncodingResult]:
        """
        Encode video to multiple profiles.
        
        Args:
            video_path: Path to source video
            profiles: List of VideoEncodingProfile instances
            video_id: Video ID for filenames
            parallel: Whether to encode in parallel
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of EncodingResult for each profile
        """
        if not profiles:
            logger.warning("[ENCODE] No profiles provided")
            return []
        
        # Filter suitable profiles
        suitable_profiles = get_suitable_profiles(video_path, profiles)
        logger.info(f"[ENCODE] Encoding {len(suitable_profiles)} profiles for video {video_id}")
        
        if parallel and len(suitable_profiles) > 1:
            return self._encode_parallel(
                video_path, suitable_profiles, video_id, progress_callback
            )
        else:
            return self._encode_sequential(
                video_path, suitable_profiles, video_id, progress_callback
            )
    
    def _encode_sequential(
        self,
        video_path: str,
        profiles: list,
        video_id: int,
        progress_callback: Optional[Callable]
    ) -> List[EncodingResult]:
        """Encode profiles one by one."""
        results = []
        total = len(profiles)
        
        for i, profile in enumerate(profiles):
            if progress_callback:
                progress = int((i / total) * 100)
                progress_callback(progress, f"Encoding {profile.resolution}...")
            
            result = self.encode_single(video_path, profile, video_id)
            results.append(result)
            
            if not result.success:
                logger.error(f"[ENCODE] Stopping due to failure on {profile.resolution}")
                break
        
        return results
    
    def _encode_parallel(
        self,
        video_path: str,
        profiles: list,
        video_id: int,
        progress_callback: Optional[Callable]
    ) -> List[EncodingResult]:
        """Encode profiles in parallel with limited concurrency."""
        results = []
        completed = 0
        total = len(profiles)
        
        # Limit parallel jobs to avoid overloading
        max_workers = min(self.MAX_PARALLEL_JOBS, len(profiles))
        logger.info(f"[ENCODE] Starting parallel encoding with {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.encode_single, video_path, profile, video_id
                ): profile
                for profile in profiles
            }
            
            for future in as_completed(futures):
                profile = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    if progress_callback:
                        progress = int((completed / total) * 100)
                        status = "completed" if result.success else "failed"
                        progress_callback(
                            progress, 
                            f"Encoded {profile.resolution} ({status})"
                        )
                        
                except Exception as e:
                    logger.error(f"[ENCODE] Exception for {profile.resolution}: {e}")
                    results.append(EncodingResult(
                        profile_name=profile.name,
                        resolution=profile.resolution,
                        success=False,
                        error_message=str(e)
                    ))
        
        return results
    
    def cleanup_encoded_files(self, results: List[EncodingResult]) -> int:
        """
        Remove encoded files (for cleanup on error).
        
        Returns:
            Number of files removed
        """
        removed = 0
        for result in results:
            if result.output_path and os.path.exists(result.output_path):
                try:
                    os.remove(result.output_path)
                    logger.info(f"[ENCODE] Cleaned up: {result.output_path}")
                    removed += 1
                except Exception as e:
                    logger.warning(f"[ENCODE] Cleanup failed: {e}")
        return removed
    
    def get_encoding_stats(self, results: List[EncodingResult]) -> Dict[str, Any]:
        """Get statistics from encoding results."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        total_size = sum(r.file_size for r in successful)
        total_time = sum(r.duration_seconds for r in results)
        
        return {
            "total_profiles": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_size_bytes": total_size,
            "total_size_mb": total_size // (1024 * 1024),
            "total_time_seconds": total_time,
            "profiles": [
                {
                    "name": r.profile_name,
                    "resolution": r.resolution,
                    "success": r.success,
                    "size_mb": r.file_size // (1024 * 1024) if r.success else 0,
                    "time_seconds": r.duration_seconds
                }
                for r in results
            ]
        }
