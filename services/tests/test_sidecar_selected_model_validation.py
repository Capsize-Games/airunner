"""Selected-model validation must raise RuntimeError, not NameError.

Regression: the offload-mismatch branch evaluated ``os.environ`` without
importing ``os``, so a CPU-profile settings object with a mismatched
GPU-layer selection crashed with NameError instead of the documented
RuntimeError.
"""

from __future__ import annotations

import pytest

from airunner_services.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)
from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient


def _settings(model_path: str) -> LlamaCppRuntimeSettings:
    return LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=0,
        model_path=model_path,
        model_id=None,
        runtime_profile="default",
        n_ctx=2048,
        n_gpu_layers=0,
        startup_timeout_seconds=1.0,
        backend_profile="cpu",
    )


def test_mismatched_gpu_layers_raise_runtime_error(tmp_path, monkeypatch) -> None:
    model = tmp_path / "model.gguf"
    model.write_bytes(b"GGUF")
    monkeypatch.delenv("AIRUNNER_LLAMA_BACKEND", raising=False)

    with pytest.raises(RuntimeError, match="offload does not match"):
        SidecarLLMClient._validate_selected_model(
            _settings(str(model)),
            {
                "model_path": str(model),
                "model_id": None,
                "n_ctx": None,
                "n_gpu_layers": 12,
            },
        )
