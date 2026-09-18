"""Timing and memory helpers for the canvas benchmark harness (#2231)."""

from __future__ import annotations

import statistics
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Callable, Dict, List


def rss_mb() -> float:
    """Return the process resident set size in MiB."""
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        return 0.0
    return 0.0


def _p95(samples: List[float]) -> float:
    ordered = sorted(samples)
    index = int(round(0.95 * (len(ordered) - 1)))
    return ordered[min(index, len(ordered) - 1)]


@dataclass
class Result:
    """Wall-clock samples (ms) for one scenario."""

    name: str
    samples_ms: List[float] = field(default_factory=list)

    def add(self, milliseconds: float) -> None:
        """Record one sample."""
        self.samples_ms.append(milliseconds)

    def summary(self) -> Dict[str, float]:
        """Return count/mean/p50/p95/max in ms."""
        if not self.samples_ms:
            return {"count": 0}
        return {
            "count": len(self.samples_ms),
            "mean_ms": round(statistics.fmean(self.samples_ms), 3),
            "p50_ms": round(statistics.median(self.samples_ms), 3),
            "p95_ms": round(_p95(self.samples_ms), 3),
            "max_ms": round(max(self.samples_ms), 3),
        }


def measure(result: Result, fn: Callable[[], None], reps: int) -> None:
    """Run ``fn`` ``reps`` times, recording wall-clock ms per call."""
    for _ in range(reps):
        start = time.perf_counter()
        fn()
        result.add((time.perf_counter() - start) * 1000.0)


def peak_tracemalloc_mb() -> float:
    """Return the peak traced allocation in MiB (tracemalloc must be on)."""
    _, peak = tracemalloc.get_traced_memory()
    return peak / (1024.0 * 1024.0)
