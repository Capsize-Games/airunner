"""Contract between the LLM mixins and HardwareProfiler (issue #2242).

The P09 diagnostics refactor replaced
``HardwareProfiler._get_available_vram_gb`` with
``get_profile().available_vram_gb`` but left two mixin callers on the
old name, so every LLM generate failed with AttributeError and the
functional e2e test observed an empty 200. These tests exercise both
callers against the real profiler (no mocks) so the next profiler
refactor breaks loudly here instead of in production.
"""

from __future__ import annotations

from airunner_services.llm.managers.mixins.property_mixin import (
    PropertyMixin,
)
from airunner_services.llm.quantization_mixin import QuantizationMixin


class _QuantizationProbe(QuantizationMixin):
    """Minimal host for the quantization mixin under test."""


class _PropertyProbe(PropertyMixin):
    """Minimal host for the property mixin under test."""


def test_quantization_mixin_reads_real_profiler() -> None:
    """Quantization VRAM probing must match the profiler API."""
    vram_gb = _QuantizationProbe()._get_available_vram_gb()
    assert isinstance(vram_gb, float)
    assert vram_gb >= 0.0


def test_property_mixin_reads_real_profiler() -> None:
    """Property VRAM probing must match the profiler API."""
    vram_gb = _PropertyProbe()._get_available_vram_gb()
    assert isinstance(vram_gb, float)
    assert vram_gb >= 0.0
