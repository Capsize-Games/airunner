"""Environment-based configuration for the video runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODELS_DIR = "~/.local/share/airunner/models/video"
DEFAULT_OUTPUT_DIR = "~/.local/share/airunner/video-output"
FP8_REPO = "Lightricks/LTX-2.3"
NVFP4_REPO = "protoLabsAI/LTX-2.3-22B-distilled-NVFP4"


@dataclass(frozen=True)
class VideoConfig:
    """Resolved video runtime settings (env is the only source)."""

    models_dir: str = DEFAULT_MODELS_DIR
    output_dir: str = DEFAULT_OUTPUT_DIR
    idle_unload_s: float = 300.0
    max_queue: int = 4

    @classmethod
    def from_env(cls) -> VideoConfig:
        """Build config from AIRUNNER_VIDEO_* environment variables."""
        return cls(
            models_dir=os.environ.get(
                "AIRUNNER_VIDEO_MODELS_DIR", DEFAULT_MODELS_DIR
            ),
            output_dir=os.environ.get(
                "AIRUNNER_VIDEO_OUTPUT_DIR", DEFAULT_OUTPUT_DIR
            ),
            idle_unload_s=float(
                os.environ.get("AIRUNNER_VIDEO_IDLE_UNLOAD_S", "300")
            ),
            max_queue=int(os.environ.get("AIRUNNER_VIDEO_MAX_QUEUE", "4")),
        )

    def checkpoint_dir(self, checkpoint: str) -> Path:
        """Return the on-disk directory for one checkpoint id."""
        name = "ltx-2.3-fp8" if checkpoint == "fp8" else "ltx-2.3-nvfp4"
        return Path(self.models_dir).expanduser() / name
