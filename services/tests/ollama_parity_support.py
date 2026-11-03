"""Loopback server plus canned LLM doubles for Ollama parity tests.

Issue #2237 (Model UX step): shared fixtures behind
``test_ollama_client_parity`` so the parity suite stays small while
the doubles remain reusable for future compat-route coverage.
"""

from __future__ import annotations

import os
import socket
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI

from airunner_common.contract_enums import ModelStatus
from airunner_common.contract_enums import ModelType
from airunner_services.api.server import create_app
from airunner_services.utils.job_tracker import JobState
from airunner_services.utils.job_tracker import JobStatus

CANNED_CHUNKS = ("Hello", " from", " AIRunner")
CANNED_TEXT = "".join(CANNED_CHUNKS)
SERVER_START_TIMEOUT_SECONDS = 15.0
SERVER_POLL_SECONDS = 0.05


@dataclass
class CannedResponse:
    """One canned LLM reply shaped like a real worker response."""

    message: str
    is_end_of_message: bool
    message_type: Optional[str] = None
    tool_calls: Optional[list[Any]] = None
    final_visible_message: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class FakeLLM:
    """LLM double that emits canned chunks, then a terminal event."""

    def send_request(self, **kwargs: Any) -> None:
        """Invoke the chat callback once per chunk plus terminal."""
        callback: Callable[[dict[str, Any]], None] = kwargs["callback"]
        for chunk in CANNED_CHUNKS:
            callback({"response": CannedResponse(chunk, False)})
        callback(
            {
                "response": CannedResponse(
                    "",
                    True,
                    prompt_tokens=6,
                    completion_tokens=3,
                    total_tokens=9,
                )
            }
        )


class FakeBalancer:
    """Model-load balancer double reporting a loaded local LLM."""

    def get_loaded_models(self) -> list[ModelType]:
        """Return a loaded-LLM marker so readiness checks pass."""
        return [ModelType.LLM]


class FakeApp:
    """Minimal app surface for Ollama routes with a canned LLM."""

    def __init__(self) -> None:
        self.llm = FakeLLM()
        self.model_load_balancer = FakeBalancer()
        self._model_fixture_dir = tempfile.TemporaryDirectory(
            prefix="airunner-ollama-parity-"
        )
        model_path = os.path.join(
            self._model_fixture_dir.name, "Qwen3.5-9B-Q8_0.gguf"
        )
        with open(model_path, "wb") as artifact:
            artifact.write(b"ollama route metadata fixture")
        model_manager = type(
            "FakeModelManager",
            (),
            {
                "model_status": {ModelType.LLM: ModelStatus.LOADED},
                "_current_model_path": model_path,
                "_resolve_model_id_from_path": lambda _self, _path: "qwen3.5-9b",
                "_chat_model": type("FakeChatModel", (), {"n_ctx": 32768})(),
            },
        )()
        worker = type(
            "FakeLLMWorker",
            (),
            {
                "_model_manager": model_manager,
                "current_model_status": lambda _self: ModelStatus.LOADED,
            },
        )()
        self._worker_manager = type(
            "FakeWorkerManager", (), {"_llm_generate_worker": worker}
        )()

    def emit_signal(self, _code: Any, _data: Any = None) -> None:
        """Ignore signal emissions during canned-client tests."""


class FakeDownloadJobService:
    """Controlled download-job states; never performs a network request."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.default_states = [
            JobState("fake-job", JobStatus.PENDING, progress=0.0),
            JobState("fake-job", JobStatus.RUNNING, progress=35.0),
            JobState("fake-job", JobStatus.COMPLETED, progress=100.0),
        ]
        self.states = self.default_states
        self.next_states: list[JobState] | None = None
        self._position = 0

    async def start_huggingface_download(self, **kwargs: Any) -> str:
        """Record the normalized target and start a deterministic fake job."""
        self.calls.append(kwargs)
        self.states = (
            self.next_states
            if self.next_states is not None
            else self.default_states
        )
        self.next_states = None
        self._position = 0
        return "fake-job"

    async def get_status(self, job_id: str) -> JobState | None:
        """Return the next controlled status for the requested job."""
        if job_id != "fake-job" or not self.states:
            return None
        position = min(self._position, len(self.states) - 1)
        self._position += 1
        return self.states[position]


def free_loopback_port() -> int:
    """Return one currently-free loopback TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def served_app(port: int) -> uvicorn.Server:
    """Return a uvicorn server for the compat app on one port."""
    os.environ["AIRUNNER_INSECURE_NO_AUTH"] = "1"
    # The parity suite makes several sequential pull requests against one
    # process. Keep those deterministic integration cases independent of the
    # production setup rate limit; admission behavior has its own tests.
    os.environ["AIRUNNER_SETUP_REQUESTS_PER_MINUTE"] = "1000"
    app: FastAPI = create_app(
        allowed_origins=["http://localhost"],
        enable_cors=False,
        app_instance=FakeApp(),
    )
    app.state.download_job_service = FakeDownloadJobService()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    return uvicorn.Server(config)


def wait_for_server(server: uvicorn.Server) -> None:
    """Block until the server accepts connections or time out."""
    deadline = time.time() + SERVER_START_TIMEOUT_SECONDS
    while not server.started:
        if time.time() > deadline:
            raise TimeoutError("uvicorn test server never started")
        time.sleep(SERVER_POLL_SECONDS)
