"""
Video processing services package.

This package contains modular services for video processing:
- ffmpeg_wrapper: Low-level FFmpeg command execution
- poster_service: Poster/thumbnail extraction
- preview_service: Preview video generation
- encoding_service: Video encoding to different profiles
- hls_service: HLS (HTTP Live Streaming) generation
- dash_service: DASH (Dynamic Adaptive Streaming) generation
- processing_pipeline: Orchestration of the full pipeline
"""

from .ffmpeg_wrapper import FFmpegWrapper, FFmpegResult, get_suitable_profiles
from .poster_service import PosterService
from .preview_service import PreviewService
from .encoding_service import EncodingService, EncodingResult
from .hls_service import HLSService
from .dash_service import DASHService
from .processing_pipeline import ProcessingPipeline, PipelineConfig, PipelineResult

__all__ = [
    'FFmpegWrapper',
    'FFmpegResult',
    'get_suitable_profiles',
    'PosterService',
    'PreviewService',
    'EncodingService',
    'EncodingResult',
    'HLSService',
    'DASHService',
    'ProcessingPipeline',
    'PipelineConfig',
    'PipelineResult',
]
