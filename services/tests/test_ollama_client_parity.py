"""Real-client parity for the Ollama compatibility routes (issue #2237).

Route existence is pinned by ``test_legacy_api_surface``; these tests
drive ``/api/chat`` and ``/api/generate`` the way a real Ollama client
does. The FastAPI app is served over loopback with a canned LLM
double and exercised through the real ``ollama`` Python client,
asserting the NDJSON streaming protocol, terminal-chunk shapes,
metadata parsing, and error mapping.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from unittest.mock import patch

import ollama
import pytest

from ollama_parity_support import CANNED_TEXT
from ollama_parity_support import SERVER_START_TIMEOUT_SECONDS
from ollama_parity_support import free_loopback_port
from ollama_parity_support import served_app
from ollama_parity_support import wait_for_server
from airunner_services.utils.job_tracker import JobState
from airunner_services.utils.job_tracker import JobStatus


@pytest.fixture(scope="module")
def ollama_server() -> Iterator[object]:
    """Serve the compat app with only canned LLM and download jobs."""
    port = free_loopback_port()
    with patch(
        "airunner_services.api.routes.legacy_ollama_compat.configured_model_basename",
        return_value="qwen3.5-9b",
    ):
        server = served_app(port)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        wait_for_server(server)
        yield server
        server.should_exit = True
        thread.join(timeout=SERVER_START_TIMEOUT_SECONDS)


@pytest.fixture(scope="module")
def ollama_client(ollama_server) -> ollama.Client:
    """Return the real Ollama client bound to the fake service server."""
    return ollama.Client(
        host=f"http://127.0.0.1:{ollama_server.config.port}"
    )


@pytest.fixture(scope="module")
def listed_model(ollama_client: ollama.Client) -> str:
    """Return the configured model name the daemon advertises."""
    return str(ollama_client.list().models[0].model)


@pytest.mark.fast
def test_list_models_parses(ollama_client: ollama.Client) -> None:
    """The real client parses our /api/tags payload."""
    models = ollama_client.list().models
    assert len(models) == 1
    assert str(models[0].model).endswith(":latest")
    # The fixture has no verified digest receipt, so an empty digest is the
    # truthful value and the real client still parses the model.
    assert str(models[0].digest) == ""
    assert (models[0].size or 0) > 0
    assert models[0].modified_at is not None
    assert models[0].details is not None


@pytest.mark.fast
def test_show_model_parses(
    ollama_client: ollama.Client,
) -> None:
    """The real client parses only metadata present in the model catalog."""
    shown = ollama_client.show("qwen3.5-9b")
    assert shown.modelinfo == {"context_length": 262144}
    assert "completion" in (shown.capabilities or [])
    assert "tools" in (shown.capabilities or [])
    assert shown.license is None
    assert shown.details is None
    assert shown.modelfile is None


@pytest.mark.fast
def test_ps_matches_listed_model(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """The real client sees the loaded model in /api/ps."""
    running = ollama_client.ps().models
    assert len(running) == 1
    assert running[0].model == listed_model
    # The test process has no measured GPU allocation for this fixture.
    assert (running[0].size_vram or 0) == 0


@pytest.mark.fast
def test_chat_non_stream_round_trip(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """Non-streaming chat answers with the full canned reply."""
    response = ollama_client.chat(
        model=listed_model,
        messages=[{"role": "user", "content": "Say hello"}],
        stream=False,
    )
    assert response.message.role == "assistant"
    assert response.message.content == CANNED_TEXT
    assert response.done is True
    assert response.done_reason == "stop"
    assert response.prompt_eval_count == 6
    assert response.eval_count == 3
    assert response.prompt_eval_duration == 0
    assert response.eval_duration == 0


@pytest.mark.fast
def test_chat_stream_deltas_concatenate(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """Streaming chat deltas concatenate; terminal chunk is done:true."""
    chunks = list(
        ollama_client.chat(
            model=listed_model,
            messages=[{"role": "user", "content": "Say hello"}],
            stream=True,
        )
    )
    assert len(chunks) > 1
    joined = "".join(c.message.content or "" for c in chunks)
    assert joined == CANNED_TEXT
    assert all(c.done is False for c in chunks[:-1])
    terminal = chunks[-1]
    assert terminal.done is True
    assert terminal.message.content == ""
    assert terminal.done_reason == "stop"
    assert terminal.prompt_eval_count == 6
    assert terminal.eval_count == 3
    assert {c.model for c in chunks} == {listed_model}


@pytest.mark.fast
def test_generate_non_stream_round_trip(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """Non-streaming generate answers with the full canned reply."""
    response = ollama_client.generate(
        model=listed_model, prompt="Say hello", stream=False
    )
    assert response.response == CANNED_TEXT
    assert response.done is True
    assert response.prompt_eval_count == 6
    assert response.eval_count == 3
    assert response.prompt_eval_duration == 0
    assert response.eval_duration == 0


@pytest.mark.fast
def test_generate_stream_chunks(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """Streaming generate deltas concatenate to the canned reply."""
    chunks = list(
        ollama_client.generate(
            model=listed_model, prompt="Say hello", stream=True
        )
    )
    assert len(chunks) > 1
    joined = "".join(c.response or "" for c in chunks)
    assert joined == CANNED_TEXT
    assert chunks[-1].done is True
    assert chunks[-1].response == ""
    assert chunks[-1].prompt_eval_count == 6
    assert chunks[-1].eval_count == 3


@pytest.mark.fast
def test_chat_rejects_empty_messages(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """Chat without messages surfaces the daemon's 400 to the client."""
    with pytest.raises(ollama.ResponseError) as exc_info:
        ollama_client.chat(model=listed_model, messages=[])
    assert exc_info.value.status_code == 400


@pytest.mark.fast
def test_generate_rejects_empty_prompt(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """Generate without a prompt surfaces the daemon's 400."""
    with pytest.raises(ollama.ResponseError) as exc_info:
        ollama_client.generate(model=listed_model, prompt="")
    assert exc_info.value.status_code == 400


@pytest.mark.fast
def test_pull_stream_ends_in_success(
    ollama_client: ollama.Client, ollama_server
) -> None:
    """Streaming pull reflects fake job progress and ends on completion."""
    statuses = [
        chunk.status
        for chunk in ollama_client.pull("qwen3.5-9b", stream=True)
    ]
    assert len(statuses) > 1
    assert statuses[-1] == "success"
    service = ollama_server.config.app.state.download_job_service
    assert service.calls[-1] == {
        "repo_id": "unsloth/Qwen3.5-9B-GGUF",
        "model_type": "gguf",
        "gguf_filename": "Qwen3.5-9B-Q8_0.gguf",
        "prefer_pre_quantized": True,
    }


@pytest.mark.fast
def test_pull_stream_includes_real_job_progress(
    ollama_client: ollama.Client,
) -> None:
    """NDJSON carries progress from JobState without invented byte totals."""
    response = ollama_client._client.post(
        "/api/pull",
        json={"model": "qwen3.5-9b", "stream": True},
    )
    assert response.status_code == 200
    records = [json.loads(line) for line in response.text.splitlines()]
    assert records[0] == {"status": "starting"}
    assert {"status": "downloading", "progress": 35.0} in records
    assert records[-1] == {"status": "success"}


@pytest.mark.fast
def test_pull_non_stream_waits_for_job_success(
    ollama_client: ollama.Client,
) -> None:
    """Non-streaming pull returns success only after completion."""
    result = ollama_client.pull("qwen3.5-9b", stream=False)
    assert result.status == "success"


@pytest.mark.fast
def test_pull_requires_a_boolean_stream_flag(
    ollama_client: ollama.Client, ollama_server
) -> None:
    """String values such as "false" are rejected without starting work."""
    service = ollama_server.config.app.state.download_job_service
    initial_calls = len(service.calls)
    response = ollama_client._client.post(
        "/api/pull",
        json={"model": "qwen3.5-9b", "stream": "false"},
    )
    assert response.status_code == 400
    assert len(service.calls) == initial_calls


@pytest.mark.fast
def test_show_unknown_model_is_not_found(
    ollama_client: ollama.Client,
) -> None:
    with pytest.raises(ollama.ResponseError) as exc_info:
        ollama_client.show("not-in-the-local-catalog")
    assert exc_info.value.status_code == 404


@pytest.mark.fast
def test_show_configured_non_catalog_model_is_minimal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured custom models show no invented catalog metadata."""
    from airunner_services.api.routes import legacy_ollama_compat

    monkeypatch.setattr(
        legacy_ollama_compat,
        "configured_model_basename",
        lambda: "custom-local-model",
    )
    response = legacy_ollama_compat.ollama_show(
        {"model": "custom-local-model:latest"}
    )
    assert response == {"model_info": {}, "capabilities": []}


@pytest.mark.fast
def test_pull_unknown_model_is_not_found(
    ollama_client: ollama.Client,
) -> None:
    with pytest.raises(ollama.ResponseError) as exc_info:
        ollama_client.pull("not-in-the-local-catalog", stream=False)
    assert exc_info.value.status_code == 404


@pytest.mark.fast
def test_pull_stream_reports_job_failure(
    ollama_client: ollama.Client, ollama_server
) -> None:
    """A failed fake job emits the Ollama stream error terminal record."""
    service = ollama_server.config.app.state.download_job_service
    service.next_states = [
        JobState("fake-job", JobStatus.RUNNING, progress=10.0),
        JobState("fake-job", JobStatus.FAILED, progress=10.0),
    ]
    with pytest.raises(ollama.ResponseError, match="Model pull failed"):
        list(ollama_client.pull("qwen3.5-9b", stream=True))


@pytest.mark.fast
def test_pull_non_stream_reports_job_failure(
    ollama_client: ollama.Client, ollama_server
) -> None:
    """A failed job cannot return non-stream success."""
    service = ollama_server.config.app.state.download_job_service
    service.next_states = [
        JobState("fake-job", JobStatus.RUNNING, progress=12.0),
        JobState("fake-job", JobStatus.FAILED, progress=12.0),
    ]
    with pytest.raises(ollama.ResponseError) as exc_info:
        ollama_client.pull("qwen3.5-9b", stream=False)
    assert exc_info.value.status_code == 502
    assert service._position >= 2


@pytest.mark.fast
def test_pull_stream_timeout_is_an_error_terminal(
    ollama_client: ollama.Client,
    ollama_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from airunner_services.api.routes import ollama_pull_helpers
    from airunner_services.utils.job_tracker import JobState
    from airunner_services.utils.job_tracker import JobStatus

    monkeypatch.setattr(
        ollama_pull_helpers,
        "pull_timeouts",
        lambda: (0.006, 0.02, 0.001),
    )
    service = ollama_server.config.app.state.download_job_service
    service.next_states = [
        JobState("fake-job", JobStatus.RUNNING, progress=10.0)
    ]
    with pytest.raises(
        ollama.ResponseError,
        match="Model pull observation timed out",
    ):
        list(ollama_client.pull("qwen3.5-9b", stream=True))
    assert service.states[-1].status is JobStatus.RUNNING


@pytest.mark.fast
def test_pull_nonstream_timeout_is_http_504(
    ollama_client: ollama.Client,
    ollama_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from airunner_services.api.routes import ollama_pull_helpers
    from airunner_services.utils.job_tracker import JobState
    from airunner_services.utils.job_tracker import JobStatus

    monkeypatch.setattr(
        ollama_pull_helpers,
        "pull_timeouts",
        lambda: (0.006, 0.02, 0.001),
    )
    service = ollama_server.config.app.state.download_job_service
    service.next_states = [
        JobState("fake-job", JobStatus.RUNNING, progress=10.0)
    ]
    with pytest.raises(ollama.ResponseError) as exc_info:
        ollama_client.pull("qwen3.5-9b", stream=False)
    assert exc_info.value.status_code == 504
    assert service.states[-1].status is JobStatus.RUNNING


@pytest.mark.fast
def test_pull_respects_offline_provider_policy(
    ollama_client: ollama.Client,
    ollama_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared job service rejects pulls before creating a job offline."""
    from airunner_common import settings as airunner_settings
    from airunner_services.downloads.job_service import DownloadJobService

    app = ollama_server.config.app
    fake_service = app.state.download_job_service
    real_service = DownloadJobService()
    monkeypatch.setattr(app.state, "download_job_service", real_service)
    monkeypatch.setattr(airunner_settings, "AIRUNNER_OFFLINE_MODE", True)
    try:
        with pytest.raises(ollama.ResponseError) as exc_info:
            ollama_client.pull("qwen3.5-9b", stream=False)
        assert exc_info.value.status_code == 403
        assert "provider_download_disabled" in exc_info.value.error
        assert real_service._tracker.get_all_jobs() == {}
    finally:
        app.state.download_job_service = fake_service
