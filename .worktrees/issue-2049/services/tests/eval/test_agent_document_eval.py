"""Daemon-backed evals for attached-document analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_eval_support import assert_tool_names
from agent_eval_support import build_agent_request
from agent_eval_support import run_agent_eval_case
from llm_functional_support import combined_llama_env_overrides
from llm_functional_support import daemon_env
from llm_functional_support import llm_artifact_path
from llm_functional_support import started_daemon


_MODEL_IDS = ["qwen3.5-9b", "gpt-oss-20b"]
_DOCUMENT_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "agent_eval_document.md"
)
_TIME_MACHINE_FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "rag_formats"
    / "the-time-machine"
)
_TIME_MACHINE_PATHS = [
    _TIME_MACHINE_FIXTURE_DIR / "source.epub",
    _TIME_MACHINE_FIXTURE_DIR / "source.mobi",
    _TIME_MACHINE_FIXTURE_DIR / "source.pdf",
]
_TIME_MACHINE_MORLOCKS_PROMPT = (
    "Use the loaded document search tool to search the attached document "
    "for the exact term Morlocks. After the tool result, answer with "
    "exactly Morlocks only."
)


def _document_daemon_env(model_id: str) -> dict[str, str]:
    """Return stable daemon env overrides for document evals."""
    extra_env = combined_llama_env_overrides(model_id)
    extra_env["CUDA_VISIBLE_DEVICES"] = ""
    if model_id == "qwen3.5-9b":
        extra_env["AIRUNNER_GGUF_N_GPU_LAYERS"] = "0"
        extra_env["AIRUNNER_LOCAL_FALLBACK_TIMEOUT_SECONDS"] = "900"
    return daemon_env(
        llm_on=True,
        tts_on=False,
        extra_env=extra_env,
    )


def _time_machine_daemon_env(model_id: str) -> dict[str, str]:
    """Return stable env overrides for the heavier tri-format fixture."""
    return _document_daemon_env(model_id)


def _document_request(
    model_id: str,
    prompt: str,
    document_path: Path = _DOCUMENT_PATH,
    max_new_tokens: int = 64,
) -> dict[str, object]:
    """Build one attached-document eval request."""
    return build_agent_request(
        model_id,
        prompt,
        tool_categories=["rag"],
        rag_files=[str(document_path)],
        force_tool="rag_search",
        max_new_tokens=max_new_tokens,
    )


def _read_log_text(log_path: str) -> str:
    """Return daemon log text for deterministic RAG assertions."""
    return Path(log_path).read_text(encoding="utf-8", errors="replace")


def _assert_rag_search_log(
    log_path: str,
    *anchors: str,
    previous_log_text: str = "",
    result_count: int | None = 1,
) -> None:
    """Assert that rag_search logged the expected result count and anchors."""
    log_text = _read_log_text(log_path)[len(previous_log_text) :]
    assert "Tool completed: rag_search - found results" in log_text, log_text
    if result_count is None:
        assert "rag_manager.search returned" in log_text, log_text
    else:
        expected = f"rag_manager.search returned {result_count} results"
        assert expected in log_text, log_text
    for anchor in anchors:
        assert anchor in log_text, log_text


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
        "Use the loaded document search tool to search the attached "
        "document for the exact phrase Project Alpha. After the tool "
        "result, answer with exactly Project Alpha only."
    )
    with started_daemon(_document_daemon_env(model_id)) as daemon:
        previous_log_text = _read_log_text(daemon.log_path)
        result = run_agent_eval_case(
            daemon.base_url,
            _document_request(model_id, prompt),
        )
        assert result.status_code == 200, _read_log_text(daemon.log_path)
        assert_tool_names(
            result,
            expected={"rag_search"},
            log_path=daemon.log_path,
        )
        _assert_rag_search_log(
            daemon.log_path,
            "Project Alpha",
            previous_log_text=previous_log_text,
        )


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
        "Use the loaded document search tool to search the attached "
        "document for the exact term 73142. After the tool result, "
        "answer with exactly 73142 only."
    )
    with started_daemon(_document_daemon_env(model_id)) as daemon:
        previous_log_text = _read_log_text(daemon.log_path)
        result = run_agent_eval_case(
            daemon.base_url,
            _document_request(model_id, prompt),
        )
        assert result.status_code == 200, _read_log_text(daemon.log_path)
        assert_tool_names(
            result,
            expected={"rag_search"},
            log_path=daemon.log_path,
        )
        _assert_rag_search_log(
            daemon.log_path,
            "Emergency code: 73142",
            previous_log_text=previous_log_text,
        )


@pytest.mark.parametrize("model_id", _MODEL_IDS, ids=_MODEL_IDS)
@pytest.mark.parametrize(
    "document_path",
    _TIME_MACHINE_PATHS,
    ids=["epub", "mobi", "pdf"],
)
@pytest.mark.eval
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(900)
def test_agent_routes_time_machine_results_through_rag_search(
    model_id: str,
    document_path: Path,
) -> None:
    """Validate tri-format Time Machine retrieval through rag_search."""
    artifact_path = llm_artifact_path(model_id)
    if not artifact_path.is_file():
        pytest.skip(f"Missing local model artifact: {artifact_path}")

    with started_daemon(_time_machine_daemon_env(model_id)) as daemon:
        previous_log_text = _read_log_text(daemon.log_path)
        result = run_agent_eval_case(
            daemon.base_url,
            _document_request(
                model_id,
                _TIME_MACHINE_MORLOCKS_PROMPT,
                document_path,
            ),
        )
        assert result.status_code == 200, _read_log_text(daemon.log_path)
        assert_tool_names(
            result,
            expected={"rag_search"},
            log_path=daemon.log_path,
        )
        _assert_rag_search_log(
            daemon.log_path,
            previous_log_text=previous_log_text,
            result_count=None,
        )