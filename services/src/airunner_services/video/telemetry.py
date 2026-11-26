"""VRAM/RAM sampling for video jobs (torch-first, psutil for RSS)."""

from __future__ import annotations

import threading
import time


class TelemetrySampler:
    """Background sampler recording peak VRAM/RSS until stopped."""

    def __init__(self, interval_s: float = 0.25) -> None:
        self._interval = interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.peak_vram_mb = 0.0
        self.peak_rss_mb = 0.0

    def _sample_once(self) -> None:
        try:
            import torch

            if torch.cuda.is_available():
                used = torch.cuda.max_memory_allocated() / 2**20
                self.peak_vram_mb = max(self.peak_vram_mb, used)
        except Exception:
            pass  # telemetry must never break generation
        try:
            import psutil

            rss = psutil.Process().memory_info().rss / 2**20
            self.peak_rss_mb = max(self.peak_rss_mb, rss)
        except Exception:
            pass

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            self._sample_once()
        self._sample_once()

    def start(self) -> None:
        """Start sampling on a daemon thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop sampling and join briefly."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


def cuda_version_tag() -> str:
    """Return e.g. 'cu129' for the installed torch, '' when unknown."""
    try:
        import torch

        version = str(torch.version.cuda or "").replace(".", "")
        return f"cu{version}" if version else ""
    except Exception:
        return ""


def nvfp4_fast_path_available() -> bool:
    """NVFP4 needs the cu130+ Blackwell fast path; cu129 falls back."""
    return cuda_version_tag() >= "cu130"
