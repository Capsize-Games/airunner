"""LTX-2.3 local video generation (daemon-owned, GPU-heavy).

Public surface: contracts + config. The pipeline and service import
torch lazily so API/MCP processes stay importable without a GPU stack.
"""

from airunner_services.video.config import VideoConfig
from airunner_services.video.contracts import (
    VideoGenerationRequest,
    VideoJobStatus,
    VideoModelInfo,
    validate_frame_count,
)

__all__ = [
    "VideoConfig",
    "VideoGenerationRequest",
    "VideoJobStatus",
    "VideoModelInfo",
    "validate_frame_count",
]
