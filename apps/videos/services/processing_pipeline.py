"""
Video processing pipeline orchestration.
"""
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any

from django.conf import settings
from django.core.files import File

from .ffmpeg_wrapper import FFmpegWrapper
from .poster_service import PosterService
from .preview_service import PreviewService
from .encoding_service import EncodingService, EncodingResult
from .hls_service import HLSService
from .dash_service import DASHService

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of the full processing pipeline."""
    success: bool
    video_id: int
    poster_path: str = ""
    preview_path: str = ""
    encoded_files: List[EncodingResult] = field(default_factory=list)
    error_message: str = ""
    error_stage: str = ""
    total_time_seconds: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the processing pipeline."""
    parallel_encoding: bool = True
    max_parallel_jobs: int = 2
    cleanup_on_error: bool = True
    check_disk_space: bool = True
    min_disk_space_mb: int = 1024


class ProcessingPipeline:
    """
    Orchestrates the full video processing pipeline.
    
    Stages:
    1. Validation (FFmpeg, disk space, source file)
    2. Poster extraction
    3. Preview generation
    4. Multi-profile encoding
    5. Cleanup and finalization
    """
    
    STAGE_INIT = "initialization"
    STAGE_VALIDATION = "validation"
    STAGE_POSTER = "poster_extraction"
    STAGE_PREVIEW = "preview_generation"
    STAGE_ENCODING = "encoding"
    STAGE_FINALIZE = "finalization"
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize pipeline with optional config."""
        self.config = config or PipelineConfig()
        self._created_files = []  # Track files for cleanup
    
    def process(
        self,
        video_id: int,
        video_path: str,
        profiles: list,
        metadata_settings,
        progress_callback: Optional[Callable] = None
    ) -> PipelineResult:
        """
        Run the full processing pipeline.
        
        Args:
            video_id: Database ID of the video
            video_path: Path to source video file
            profiles: List of VideoEncodingProfile instances
            metadata_settings: MetadataExtractionSettings instance
            progress_callback: Optional callback(percent, status)
            
        Returns:
            PipelineResult with all processing details
        """
        start_time = time.time()
        self._created_files = []
        
        def update_progress(percent: int, status: str):
            if progress_callback:
                progress_callback(percent, status)
            logger.info(f"[PIPELINE] Video {video_id}: {percent}% - {status}")
        
        try:
            # Stage 1: Validation
            update_progress(5, "Validating...")
            validation_error = self._validate(video_path)
            if validation_error:
                return PipelineResult(
                    success=False,
                    video_id=video_id,
                    error_message=validation_error,
                    error_stage=self.STAGE_VALIDATION
                )
            
            # Get video info
            update_progress(10, "Analyzing source video...")
            video_info = FFmpegWrapper.get_video_info(video_path)
            
            # Stage 2: Poster extraction
            update_progress(15, "Extracting poster...")
            poster_result = self._extract_poster(
                video_id, video_path, metadata_settings
            )
            if not poster_result[0]:
                return self._handle_error(
                    video_id, start_time,
                    poster_result[1], self.STAGE_POSTER
                )
            poster_path = poster_result[1]
            
            # Stage 3: Preview generation
            update_progress(25, "Generating preview...")
            preview_result = self._generate_preview(
                video_id, video_path, metadata_settings
            )
            if not preview_result[0]:
                return self._handle_error(
                    video_id, start_time,
                    preview_result[1], self.STAGE_PREVIEW
                )
            preview_path = preview_result[1]
            
            # Stage 4: Encoding
            update_progress(35, "Starting video encoding...")
            encoding_results = self._encode_video(
                video_id, video_path, profiles,
                lambda p, s: update_progress(35 + int(p * 0.55), s)
            )
            
            # Check if any encoding succeeded
            successful_encodes = [r for r in encoding_results if r.success]
            if not successful_encodes:
                return self._handle_error(
                    video_id, start_time,
                    "All encoding profiles failed",
                    self.STAGE_ENCODING
                )
            
            # Stage 5: Finalization
            update_progress(95, "Finalizing...")
            total_time = time.time() - start_time
            
            # Collect metrics
            metrics = self._collect_metrics(
                video_info, encoding_results, total_time
            )
            
            update_progress(100, "Processing completed!")
            
            return PipelineResult(
                success=True,
                video_id=video_id,
                poster_path=poster_path,
                preview_path=preview_path,
                encoded_files=encoding_results,
                total_time_seconds=total_time,
                metrics=metrics
            )
            
        except Exception as e:
            logger.exception(f"[PIPELINE] Unexpected error for video {video_id}")
            return self._handle_error(
                video_id, start_time,
                str(e), self.STAGE_INIT
            )
    
    def _validate(self, video_path: str) -> Optional[str]:
        """Validate prerequisites. Returns error message or None."""
        # Check FFmpeg
        if not FFmpegWrapper.check_ffmpeg_available():
            return "FFmpeg is not available"
        
        # Check source file
        if not os.path.exists(video_path):
            return f"Source video not found: {video_path}"
        
        # Check disk space
        if self.config.check_disk_space:
            has_space, free, msg = FFmpegWrapper.check_disk_space(
                settings.MEDIA_ROOT,
                self.config.min_disk_space_mb * 1024 * 1024
            )
            if not has_space:
                return msg
        
        return None
    
    def _extract_poster(
        self, video_id: int, video_path: str, metadata_settings
    ) -> tuple:
        """Extract poster. Returns (success, path_or_error)."""
        poster_service = PosterService(metadata_settings)
        
        poster_format = getattr(metadata_settings, 'poster_format', 'jpg').lower()
        poster_filename = f"poster_{video_id}.{poster_format}"
        poster_path = os.path.join(settings.MEDIA_ROOT, "posters", poster_filename)
        
        if poster_service.extract(video_path, poster_path):
            self._created_files.append(poster_path)
            return (True, poster_path)
        
        return (False, f"Poster extraction failed for video {video_id}")
    
    def _generate_preview(
        self, video_id: int, video_path: str, metadata_settings
    ) -> tuple:
        """Generate preview. Returns (success, path_or_error)."""
        preview_service = PreviewService(metadata_settings)
        
        preview_format = getattr(metadata_settings, 'preview_format', 'mp4').lower()
        preview_filename = f"preview_{video_id}.{preview_format}"
        preview_path = os.path.join(settings.MEDIA_ROOT, "previews", preview_filename)
        
        if preview_service.extract(video_path, preview_path):
            self._created_files.append(preview_path)
            return (True, preview_path)
        
        return (False, f"Preview generation failed for video {video_id}")
    
    def _encode_video(
        self,
        video_id: int,
        video_path: str,
        profiles: list,
        progress_callback: Optional[Callable]
    ) -> List[EncodingResult]:
        """Encode video to all profiles."""
        encoding_service = EncodingService(
            os.path.join(settings.MEDIA_ROOT, "videos")
        )
        encoding_service.MAX_PARALLEL_JOBS = self.config.max_parallel_jobs
        
        results = encoding_service.encode_multiple(
            video_path,
            profiles,
            video_id,
            parallel=self.config.parallel_encoding,
            progress_callback=progress_callback
        )
        
        # Track created files
        for result in results:
            if result.success and result.output_path:
                self._created_files.append(result.output_path)
        
        return results
    
    def _handle_error(
        self,
        video_id: int,
        start_time: float,
        error_message: str,
        error_stage: str
    ) -> PipelineResult:
        """Handle pipeline error with optional cleanup."""
        total_time = time.time() - start_time
        
        logger.error(
            f"[PIPELINE] Video {video_id} failed at {error_stage}: {error_message}"
        )
        
        if self.config.cleanup_on_error:
            self._cleanup_created_files()
        
        return PipelineResult(
            success=False,
            video_id=video_id,
            error_message=error_message,
            error_stage=error_stage,
            total_time_seconds=total_time
        )
    
    def _cleanup_created_files(self):
        """Remove all files created during this pipeline run."""
        for path in self._created_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"[PIPELINE] Cleaned up: {path}")
            except Exception as e:
                logger.warning(f"[PIPELINE] Cleanup failed for {path}: {e}")
        self._created_files = []
    
    def _collect_metrics(
        self,
        video_info: dict,
        encoding_results: List[EncodingResult],
        total_time: float
    ) -> Dict[str, Any]:
        """Collect processing metrics."""
        successful = [r for r in encoding_results if r.success]
        
        return {
            "source": {
                "width": video_info.get("width", 0),
                "height": video_info.get("height", 0),
                "duration": video_info.get("duration", 0),
                "bitrate": video_info.get("bitrate", 0),
            },
            "encoding": {
                "total_profiles": len(encoding_results),
                "successful": len(successful),
                "failed": len(encoding_results) - len(successful),
                "total_output_size": sum(r.file_size for r in successful),
                "encoding_time": sum(r.duration_seconds for r in encoding_results),
            },
            "pipeline": {
                "total_time": total_time,
                "parallel_encoding": self.config.parallel_encoding,
            }
        }

    def generate_hls_streams(
        self,
        video_id: int,
        video_path: str,
        profiles: list,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate HLS streams for all profiles.
        
        Returns list of HLS generation results.
        """
        hls_service = HLSService()
        hls_outputs = []
        
        for profile in profiles:
            if progress_callback:
                progress_callback(
                    0, 
                    f"Generating HLS for {profile.name}..."
                )
            
            output_dir = os.path.join(
                settings.MEDIA_ROOT, 
                "streams", 
                "hls", 
                str(video_id),
                profile.resolution
            )
            
            result = hls_service.generate(
                video_path,
                output_dir,
                profile.name,
                profile.width,
                profile.height,
                profile.bitrate,
                progress_callback
            )
            
            hls_outputs.append(result)
        
        return hls_outputs
    
    def generate_dash_streams(
        self,
        video_id: int,
        video_path: str,
        profiles: list,
        video_duration: int,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate DASH streams for all profiles.
        
        Returns list of DASH generation results.
        """
        dash_service = DASHService()
        dash_outputs = []
        
        for profile in profiles:
            if progress_callback:
                progress_callback(
                    0, 
                    f"Generating DASH for {profile.name}..."
                )
            
            output_dir = os.path.join(
                settings.MEDIA_ROOT, 
                "streams", 
                "dash", 
                str(video_id),
                profile.resolution
            )
            
            result = dash_service.generate(
                video_path,
                output_dir,
                profile.name,
                profile.width,
                profile.height,
                profile.bitrate,
                progress_callback
            )
            
            dash_outputs.append(result)
        
        return dash_outputs
