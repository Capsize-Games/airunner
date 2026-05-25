"""Functional end-to-end LLM + TTS tests using the real daemon."""

from __future__ import annotations

import json

import pytest

from llm_functional_support import BUNDLED_REFERENCE_SPEAKER
from llm_functional_support import combined_llama_env_overrides
from llm_functional_support import daemon_env
from llm_functional_support import daemon_output
from llm_functional_support import llm_artifact_path
from llm_functional_support import llm_request_payload
from llm_functional_support import post_json
from llm_functional_support import started_daemon
from llm_functional_support import tts_model_path
from llm_functional_support import visible_digits
from llm_functional_support import wait_for_log_text


_MODEL_IDS = ["qwen3-8b", "qwen3.5-9b", "gpt-oss-20b"]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(1200)
@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
def test_llm_and_tts_end_to_end_without_gui(model_id: str) -> None:
    """Run one real daemon request that generates text and speaks it."""
    if not BUNDLED_REFERENCE_SPEAKER.is_file():
        pytest.fail(
            "Bundled Bob Ross reference speaker is missing: "
            f"{BUNDLED_REFERENCE_SPEAKER}"
        )

    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    openvoice_path = tts_model_path()
    if not openvoice_path.is_dir():
        pytest.skip(f"Real OpenVoice assets are required at {openvoice_path}")

    with started_daemon(
        daemon_env(
            llm_on=True,
            tts_on=True,
            openvoice_model_path=openvoice_path,
            extra_env=combined_llama_env_overrides(model_id),
        )
    ) as daemon:
        generate_status, generate_body, _generate_type = post_json(
            f"{daemon.base_url}/llm/generate",
            llm_request_payload(model_id, do_tts_reply=True),
            timeout_seconds=600,
        )

        assert generate_status == 200, daemon_output(daemon.log_path)
        generate_payload = json.loads(generate_body.decode("utf-8"))
        digits = visible_digits(str(generate_payload.get("message") or ""))
        assert digits == "7", generate_payload

        wait_for_log_text(
            daemon.log_path,
            f"[LLM LOAD] Chat model loaded: True (model_id={model_id}",
            timeout_seconds=60,
        )
        wait_for_log_text(
            daemon.log_path,
            "TTS input (",
            timeout_seconds=120,
        )
        wait_for_log_text(
            daemon.log_path,
            "OpenVoice generate timings",
            timeout_seconds=120,
        )

        unload_status, unload_body, _unload_type = post_json(
            f"{daemon.base_url}/admin/llm/unload",
            {},
        )

        assert unload_status == 200, daemon_output(daemon.log_path)
        unload_payload = json.loads(unload_body.decode("utf-8"))
        assert unload_payload["status"] == "ok"

        tts_unload_status, tts_unload_body, _tts_unload_type = post_json(
            f"{daemon.base_url}/api/v1/daemon/runtimes/tts/unload",
            {
                "provider": "local",
                "deployment_mode": "local_fallback",
                "request_id": f"functional-tts-unload-{model_id}",
            },
        )

        assert tts_unload_status == 200, daemon_output(daemon.log_path)
        tts_unload_payload = json.loads(tts_unload_body.decode("utf-8"))
        assert tts_unload_payload["status"] in {"success", "succeeded"}