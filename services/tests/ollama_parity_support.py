"""Loopback server plus canned LLM doubles for Ollama parity tests.

Issue #2237 (Model UX step): shared fixtures behind
``test_ollama_client_parity`` so the parity suite stays small while
the doubles remain reusable for future compat-route coverage.
"""

from __future__ import annotations

import os
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI

from airunner_common.contract_enums import ModelType
from airunner_services.api.server import create_app

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


class FakeLLM:
    """LLM double that emits canned chunks, then a terminal event."""

    def send_request(self, **kwargs: Any) -> None:
        """Invoke the chat callback once per chunk plus terminal."""
        callback: Callable[[dict[str, Any]], None] = kwargs["callback"]
        for chunk in CANNED_CHUNKS:
            callback({"response": CannedResponse(chunk, False)})
        callback({"response": CannedResponse("", True)})


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

    def emit_signal(self, _code: Any, _data: Any = None) -> None:
        """Ignore signal emissions during canned-client tests."""


def free_loopback_port() -> int:
    """Return one currently-free loopback TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def served_app(port: int) -> uvicorn.Server:
    """Return a uvicorn server for the compat app on one port."""
    os.environ["AIRUNNER_INSECURE_NO_AUTH"] = "1"
    app: FastAPI = create_app(
        allowed_origins=["http://localhost"],
        enable_cors=False,
        app_instance=FakeApp(),
    )
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
