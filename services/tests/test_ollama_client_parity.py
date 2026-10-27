"""Real-client parity for the Ollama compatibility routes (issue #2237).

Route existence is pinned by ``test_legacy_api_surface``; these tests
drive ``/api/chat`` and ``/api/generate`` the way a real Ollama client
does. The FastAPI app is served over loopback with a canned LLM
double and exercised through the real ``ollama`` Python client,
asserting the NDJSON streaming protocol, terminal-chunk shapes,
metadata parsing, and error mapping.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

import ollama
import pytest

from ollama_parity_support import CANNED_TEXT
from ollama_parity_support import SERVER_START_TIMEOUT_SECONDS
from ollama_parity_support import free_loopback_port
from ollama_parity_support import served_app
from ollama_parity_support import wait_for_server


@pytest.fixture(scope="module")
def ollama_client() -> Iterator[ollama.Client]:
    """Serve the compat app and yield a real client bound to it."""
    port = free_loopback_port()
    server = served_app(port)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    wait_for_server(server)
    yield ollama.Client(host=f"http://127.0.0.1:{port}")
    server.should_exit = True
    thread.join(timeout=SERVER_START_TIMEOUT_SECONDS)


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
    assert str(models[0].digest).startswith("sha256:")
    assert (models[0].size or 0) > 0
    assert models[0].modified_at is not None
    assert models[0].details is not None


@pytest.mark.fast
def test_show_model_parses(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """The real client parses our /api/show payload."""
    shown = ollama_client.show(listed_model)
    assert f"FROM {listed_model}" in (shown.modelfile or "")
    assert "num_ctx" in (shown.parameters or "")
    assert shown.template
    assert "completion" in (shown.capabilities or [])
    assert shown.modelinfo is not None


@pytest.mark.fast
def test_ps_matches_listed_model(
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """The real client sees the loaded model in /api/ps."""
    running = ollama_client.ps().models
    assert len(running) == 1
    assert running[0].model == listed_model
    assert (running[0].size_vram or 0) > 0


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
    ollama_client: ollama.Client, listed_model: str
) -> None:
    """Streaming pull ends with a success status like real Ollama."""
    statuses = [
        chunk.status
        for chunk in ollama_client.pull(listed_model, stream=True)
    ]
    assert len(statuses) > 1
    assert statuses[-1] == "success"
