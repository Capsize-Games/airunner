"""Functional end-to-end LLM tests using the real daemon."""

from __future__ import annotations

import json

import pytest

from llm_functional_support import daemon_env
from llm_functional_support import daemon_output
from llm_functional_support import llm_artifact_path
from llm_functional_support import llm_request_payload
from llm_functional_support import post_json
from llm_functional_support import started_daemon
from llm_functional_support import visible_digits
from llm_functional_support import wait_for_log_text

_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
def test_llm_end_to_end_without_gui(model_id: str) -> None:
    """Run one real non-GUI completion through the daemon for each LLM."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    with started_daemon(daemon_env(llm_on=True, tts_on=False)) as daemon:
        generate_status, generate_body, _generate_type = post_json(
            f"{daemon.base_url}/llm/generate",
            llm_request_payload(model_id, do_tts_reply=False),
        )

        assert generate_status == 200, daemon_output(daemon.log_path)
        generate_payload = json.loads(generate_body.decode("utf-8"))
        digits = visible_digits(str(generate_payload.get("message") or ""))
        assert digits == "7", generate_payload

        wait_for_log_text(
            daemon.log_path,
            f"[LLM LOAD] Chat model loaded: True (model_id={model_id}",
        )

        unload_status, unload_body, _unload_type = post_json(
            f"{daemon.base_url}/admin/llm/unload",
            {},
        )

        assert unload_status == 200, daemon_output(daemon.log_path)
        unload_payload = json.loads(unload_body.decode("utf-8"))
        assert unload_payload["status"] == "ok"
