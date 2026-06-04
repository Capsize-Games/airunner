"""Daemon-backed evals for automatic agent mood updates."""

from __future__ import annotations

import pytest

from airunner_services.database.models.conversation import Conversation

from agent_eval_support import build_agent_request
from agent_eval_support import run_agent_eval_case
from llm_functional_support import combined_llama_env_overrides
from llm_functional_support import daemon_env
from llm_functional_support import llm_artifact_path
from llm_functional_support import started_daemon
from llm_functional_support import wait_for_log_text

_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]
_MOOD_CASES = [
    pytest.param(
        "thanks, that was really helpful",
        "happy",
        id="happy",
    ),
    pytest.param(
        "this is stupid and I hate it",
        "frustrated",
        id="frustrated",
    ),
    pytest.param(
        "I am confused and do not understand what you mean",
        "confused",
        id="confused",
    ),
]


def _mood_daemon_env(model_id: str) -> dict[str, str]:
    """Return daemon env overrides for deterministic mood evals."""
    extra_env = combined_llama_env_overrides(model_id)
    extra_env.update(
        {
            "AIRUNNER_LLM_AGENT_UPDATE_MOOD_AFTER_N_TURNS": "1",
            "AIRUNNER_LLM_PRINT_SYSTEM_PROMPT": "1",
        }
    )
    return daemon_env(
        extra_env=extra_env,
    )


def _seed_conversation() -> int:
    """Create one persisted conversation with a prior user turn."""
    conversation = Conversation.create()
    assert conversation is not None
    Conversation.objects.update(
        conversation.id,
        value=[{"role": "user", "content": "Hello there."}],
    )
    return int(conversation.id)


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.parametrize(("prompt", "expected_mood"), _MOOD_CASES)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_updates_mood_from_followup_turn(
    model_id: str,
    prompt: str,
    expected_mood: str,
) -> None:
    """Update agent mood from one persisted prior user turn."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    conversation_id = _seed_conversation()
    with started_daemon(_mood_daemon_env(model_id)) as daemon:
        payload = build_agent_request(
            model_id,
            prompt,
            tool_categories=[],
            use_memory=True,
            conversation_id=conversation_id,
            max_new_tokens=32,
        )
        result = run_agent_eval_case(daemon.base_url, payload)
        assert result.status_code == 200, result.payload
        wait_for_log_text(
            daemon.log_path,
            f"[AUTO MOOD] Updated to: {expected_mood}",
        )