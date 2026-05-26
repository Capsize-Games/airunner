"""Daemon-backed evals for attached-document analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.tests.eval.agent_eval_support import assert_success
from api.tests.eval.agent_eval_support import assert_tool_names
from api.tests.eval.agent_eval_support import build_agent_request
from api.tests.eval.agent_eval_support import run_agent_eval_case
from api.tests.llm_functional_support import combined_llama_env_overrides
from api.tests.llm_functional_support import daemon_env
from api.tests.llm_functional_support import llm_artifact_path
from api.tests.llm_functional_support import started_daemon


_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]
_DOCUMENT_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "agent_eval_document.md"
)


def _document_daemon_env(model_id: str) -> dict[str, str]:
    """Return stable daemon env overrides for document evals."""
    return daemon_env(
        llm_on=True,
        tts_on=False,
        extra_env=combined_llama_env_overrides(model_id),
    )


def _document_request(model_id: str, prompt: str) -> dict[str, object]:
    """Build one attached-document eval request."""
    return build_agent_request(
        model_id,
        prompt,
        tool_categories=["rag"],
        rag_files=[str(_DOCUMENT_PATH)],
        force_tool="rag_search",
        max_new_tokens=128,
    )


def _read_log_text(log_path: str) -> str:
    """Return daemon log text for deterministic RAG assertions."""
    return Path(log_path).read_text(encoding="utf-8", errors="replace")


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_routes_codename_document_result_through_rag_search(
    model_id: str,
) -> None:
    """Validate attached-document codename retrieval through rag_search."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    prompt = (
        "Use the loaded document search tool to find the codename in the "
        "attached document. After the tool result, answer with exactly the "
        "codename only."
    )
    with started_daemon(_document_daemon_env(model_id)) as daemon:
        result = run_agent_eval_case(
            daemon.base_url,
            _document_request(model_id, prompt),
        )
        assert_success(result, daemon.log_path)
        assert_tool_names(
            result,
            expected={"rag_search"},
            log_path=daemon.log_path,
        )
        log_text = _read_log_text(daemon.log_path)
        assert "rag_manager.search returned 1 results" in log_text, log_text
        assert "Project Alpha" in log_text, log_text


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_routes_numeric_document_result_through_rag_search(
    model_id: str,
) -> None:
    """Validate attached-document numeric retrieval through rag_search."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    prompt = (
        "Use the loaded document search tool to find the emergency code in "
        "the attached document. After the tool result, answer with digits "
        "only."
    )
    with started_daemon(_document_daemon_env(model_id)) as daemon:
        result = run_agent_eval_case(
            daemon.base_url,
            _document_request(model_id, prompt),
        )
        assert_success(result, daemon.log_path)
        assert_tool_names(
            result,
            expected={"rag_search"},
            log_path=daemon.log_path,
        )
        log_text = _read_log_text(daemon.log_path)
        assert "rag_manager.search returned 1 results" in log_text, log_text
        assert "Emergency code: 73142" in log_text, log_text