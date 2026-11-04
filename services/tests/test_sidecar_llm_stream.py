"""Failure, usage, and request-scoped cancellation tests for llama.cpp SSE."""

from __future__ import annotations

import json
import http.server
import threading
import time
from types import SimpleNamespace

import pytest

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.ipc.messages import StreamDelta
from airunner_services.api.routes.llm_chat_envelope import client_frame
from airunner_services.api.routes.llm_runtime import websocket_chunk
from airunner_services.runtimes.contracts import ChatMessage, LLMInvocationRequest
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind
from airunner_services.runtimes.llama_cpp_runtime_settings import (
    LlamaCppRuntimeSettings,
)
from airunner_services.runtimes.sidecar_llm_client import SidecarLLMClient


def _data(payload: dict) -> bytes:
    return b"data: " + json.dumps(payload).encode() + b"\n\n"


class _Launcher:
    def __init__(self, endpoint="http://127.0.0.1:18080"):
        self.endpoint = endpoint
        self.stop_calls = 0
        self.start_calls = 0

    def start(self):
        self.start_calls += 1

    def stop(self):
        self.stop_calls += 1


class _Response:
    def __init__(self, lines=()):
        self.lines = iter(lines)
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def readline(self):
        if self.closed:
            return b""
        return next(self.lines, b"")

    def close(self):
        self.closed = True

    def interrupt(self):
        self.closed = True


def _client(opener=None, *, endpoint="http://127.0.0.1:18080", launcher=None):
    settings = LlamaCppRuntimeSettings(
        executable="llama-server",
        host="127.0.0.1",
        port=18080,
        model_path=None,
        model_id=None,
        runtime_profile="default",
        n_ctx=4096,
        n_gpu_layers=0,
        startup_timeout_seconds=1,
    )
    kwargs = {"http_opener": opener} if opener is not None else {}
    return SidecarLLMClient(
        settings=settings,
        launcher=launcher or _Launcher(endpoint),
        **kwargs,
    )


def _request(request_id="stream-1"):
    invocation = LLMInvocationRequest(
        messages=[ChatMessage(role="user", content="hello")], stream=True
    )
    return SimpleNamespace(
        runtime=RuntimeKind.LLM,
        action=RuntimeAction.INVOKE,
        request_id=request_id,
        payload=invocation.model_dump(),
    )


def test_sse_usage_is_preserved_on_terminal_event():
    client = _client()
    response = _Response(
        [
            _data({"choices": [{"delta": {"content": "ok"}}]}),
            _data({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
            _data({"choices": [], "usage": {"prompt_tokens": 7, "completion_tokens": 1}}),
            b"data: [DONE]\n\n",
        ]
    )

    events = list(client._stream_response("r", response))

    assert events[-1].final is True
    assert events[-1].metadata["usage"] == {
        "prompt_tokens": 7,
        "completion_tokens": 1,
    }
    assert events[-1].status is EnvelopeStatus.STREAM


@pytest.mark.parametrize(
    "lines",
    [
        [],
        [b"data: {bad json}\n\n"],
        [b"data: [DONE]\n\n"],
        [_data({"choices": []})],
    ],
)
def test_truncated_or_malformed_sse_becomes_failed_stream(lines):
    client = _client(lambda *_args, **_kwargs: _Response(lines))

    events = list(client.stream(_request()))

    assert events[-1].status is EnvelopeStatus.FAILED
    assert events[-1].final is True
    assert len(events[-1].metadata["error"]) <= 512
    assert client._launcher.stop_calls == 0


def test_stream_read_reset_is_failed_without_stopping_server():
    class ResetResponse(_Response):
        def readline(self):
            raise ConnectionResetError("peer reset")

    client = _client(lambda *_args, **_kwargs: ResetResponse())

    events = list(client.stream(_request()))

    assert events[-1].status is EnvelopeStatus.FAILED
    assert "peer reset" not in events[-1].metadata["error"]
    assert events[-1].metadata["error"] == (
        "The local LLM sidecar connection was interrupted"
    )
    assert client._launcher.stop_calls == 0


@pytest.mark.parametrize("body", [b"", b"not json", b"{}", b'{"choices":[{}]}'])
def test_nonstream_empty_or_invalid_response_is_not_success(body):
    class BodyResponse(_Response):
        def read(self):
            return body

    client = _client(lambda *_args, **_kwargs: BodyResponse())
    request = _request("invoke")
    request.payload["stream"] = False

    response = client.invoke(request)

    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "llm_invoke_failed"
    assert client._launcher.stop_calls == 0


def test_cancel_closes_only_matching_active_stream():
    entered = threading.Event()
    entered_b = threading.Event()
    release_b = threading.Event()

    class BlockingResponse(_Response):
        def readline(self):
            entered.set()
            while not self.closed:
                time.sleep(0.005)
            raise OSError("stream closed")

    class IndependentResponse(_Response):
        def __init__(self):
            super().__init__(
                [
                    _data({
                        "choices": [{
                            "delta": {"content": "b"},
                            "finish_reason": "stop",
                        }]
                    }),
                    b"data: [DONE]\n\n",
                ]
            )

        def readline(self):
            entered_b.set()
            if not release_b.wait(2):
                raise TimeoutError("test response timed out")
            return next(self.lines, b"")

    response_a = BlockingResponse()
    response_b = IndependentResponse()
    responses = iter((response_a, response_b))
    client = _client(lambda *_args, **_kwargs: next(responses))

    stream_a = client.stream(_request("a"))
    result_a = []
    thread = threading.Thread(target=lambda: result_a.extend(stream_a))
    thread.start()
    assert entered.wait(2)
    result_b = []
    thread_b = threading.Thread(
        target=lambda: result_b.extend(client.stream(_request("b")))
    )
    thread_b.start()
    assert entered_b.wait(2)
    cancelled = client.cancel("a")
    thread.join(2)
    assert not response_b.closed
    release_b.set()
    thread_b.join(2)

    assert not thread.is_alive()
    assert not thread_b.is_alive()
    assert cancelled.status is EnvelopeStatus.CANCELLED
    assert result_a[-1].status is EnvelopeStatus.CANCELLED
    assert response_a.closed
    assert client._launcher.stop_calls == 0
    assert result_b[-1].final is True


def test_duplicate_id_and_startup_cancel_are_reserved_before_launch():
    entered_start = threading.Event()
    finish_start = threading.Event()
    opener_calls = []

    class BlockingLauncher(_Launcher):
        def start(self):
            self.start_calls += 1
            entered_start.set()
            finish_start.wait(2)

    launcher = BlockingLauncher()
    client = _client(
        lambda *_args, **_kwargs: opener_calls.append(True),
        launcher=launcher,
    )
    results = []
    thread = threading.Thread(
        target=lambda: results.extend(client.stream(_request("same-id")))
    )
    thread.start()
    assert entered_start.wait(2)

    duplicate = list(client.stream(_request("same-id")))
    assert duplicate[-1].status is EnvelopeStatus.FAILED
    assert launcher.start_calls == 1
    assert client.cancel("same-id").status is EnvelopeStatus.CANCELLED
    finish_start.set()
    thread.join(2)

    assert not thread.is_alive()
    assert results[-1].status is EnvelopeStatus.CANCELLED
    assert opener_calls == []


def test_second_request_is_cancellable_while_waiting_for_startup_lock():
    entered_start = threading.Event()
    release_start = threading.Event()
    opener_ids = []

    class BlockingLauncher(_Launcher):
        def start(self):
            self.start_calls += 1
            if self.start_calls == 1:
                entered_start.set()
                release_start.wait(2)

    def opener(request, **_kwargs):
        payload = json.loads(request.data.decode())
        opener_ids.append(payload.get("metadata", {}).get("request_id"))
        return _Response(
            [
                _data({
                    "choices": [{
                        "delta": {"content": "ok"},
                        "finish_reason": "stop",
                    }]
                }),
                b"data: [DONE]\n\n",
            ]
        )

    launcher = BlockingLauncher()
    client = _client(opener, launcher=launcher)
    first_events = []
    second_events = []
    first_thread = threading.Thread(
        target=lambda: first_events.extend(client.stream(_request("first")))
    )
    first_thread.start()
    assert entered_start.wait(2)

    second_thread = threading.Thread(
        target=lambda: second_events.extend(client.stream(_request("second")))
    )
    second_thread.start()
    deadline = time.monotonic() + 2
    reserved = False
    while time.monotonic() < deadline:
        with client._active_requests_lock:
            reserved = "second" in client._active_requests
        if reserved:
            break
        time.sleep(0.005)
    assert reserved

    started = time.monotonic()
    cancelled = client.cancel("second")
    assert time.monotonic() - started < 0.25
    assert cancelled.status is EnvelopeStatus.CANCELLED
    release_start.set()
    first_thread.join(2)
    second_thread.join(2)

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert first_events[-1].final
    assert second_events[-1].status is EnvelopeStatus.CANCELLED
    assert launcher.start_calls == 1
    assert len(opener_ids) == 1


def test_cancel_during_http_open_is_recorded_before_response_arrives():
    entered_open = threading.Event()
    release_open = threading.Event()
    response = _Response([_data({"choices": [{"delta": {"content": "late"}}]})])

    def opener(*_args, **_kwargs):
        entered_open.set()
        release_open.wait(2)
        return response

    client = _client(opener)
    results = []
    thread = threading.Thread(
        target=lambda: results.extend(client.stream(_request("opening")))
    )
    thread.start()
    assert entered_open.wait(2)
    assert client.cancel("opening").status is EnvelopeStatus.CANCELLED
    release_open.set()
    thread.join(2)

    assert not thread.is_alive()
    assert response.closed
    assert results[-1].status is EnvelopeStatus.CANCELLED


def test_active_request_blocks_profile_switch_and_unload():
    entered_start = threading.Event()
    release_start = threading.Event()

    class BlockingLauncher(_Launcher):
        def start(self):
            self.start_calls += 1
            entered_start.set()
            release_start.wait(2)

    launcher = BlockingLauncher()
    client = _client(
        lambda *_args, **_kwargs: _Response(
            [_data({"choices": [{"delta": {"content": "ok"}}]}),
             _data({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
             b"data: [DONE]\n\n"]
        ),
        launcher=launcher,
    )
    results = []
    thread = threading.Thread(
        target=lambda: results.extend(client.stream(_request("owner")))
    )
    thread.start()
    assert entered_start.wait(2)

    other = _request("different-profile")
    other.payload["metadata"]["gguf_runtime_profile"] = "combined_tts"
    assert list(client.stream(other))[-1].status is EnvelopeStatus.FAILED
    unload = _request("unload")
    unload.action = RuntimeAction.UNLOAD_MODEL
    assert client.invoke(unload).status is EnvelopeStatus.FAILED
    assert launcher.stop_calls == 0

    release_start.set()
    thread.join(2)
    assert not thread.is_alive()
    assert results[-1].final


def test_active_load_control_excludes_new_request_admission():
    entered_start = threading.Event()
    release_start = threading.Event()
    opener_calls = []

    class BlockingLauncher(_Launcher):
        def start(self):
            self.start_calls += 1
            entered_start.set()
            release_start.wait(2)

    launcher = BlockingLauncher()
    client = _client(
        lambda *_args, **_kwargs: opener_calls.append(True),
        launcher=launcher,
    )
    load_request = _request("load")
    load_request.action = RuntimeAction.LOAD_MODEL
    load_results = []
    load_thread = threading.Thread(
        target=lambda: load_results.append(client.invoke(load_request))
    )
    load_thread.start()
    assert entered_start.wait(2)

    rejected = list(client.stream(_request("during-load")))
    assert rejected[-1].status is EnvelopeStatus.FAILED
    assert opener_calls == []
    assert launcher.start_calls == 1

    release_start.set()
    load_thread.join(2)
    assert not load_thread.is_alive()
    assert load_results[0].status is EnvelopeStatus.SUCCEEDED


def test_real_http_stream_cancel_ack_is_bounded():
    request_received = threading.Event()
    release_handler = threading.Event()

    class HeldSSEHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            request_received.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.flush()
            release_handler.wait(3)

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), HeldSSEHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    client = _client(endpoint=f"http://127.0.0.1:{server.server_port}")
    results = []
    stream_thread = threading.Thread(
        target=lambda: results.extend(client.stream(_request("held-http")))
    )
    try:
        stream_thread.start()
        assert request_received.wait(2), repr(results)
        deadline = time.monotonic() + 2
        attached = False
        while time.monotonic() < deadline:
            with client._active_requests_lock:
                record = client._active_requests.get("held-http")
                attached = record is not None and record.response is not None
            if attached:
                break
            time.sleep(0.005)
        assert attached
        time.sleep(0.05)

        started = time.monotonic()
        cancelled = client.cancel("held-http")
        elapsed = time.monotonic() - started
        assert cancelled.status is EnvelopeStatus.CANCELLED
        assert elapsed < 0.25
        stream_thread.join(2)
        assert not stream_thread.is_alive()
        assert results[-1].status is EnvelopeStatus.CANCELLED
        assert client._launcher.stop_calls == 0
    finally:
        release_handler.set()
        server.shutdown()
        server.server_close()
        server_thread.join(2)


def test_real_http_nonstream_cancel_is_request_scoped():
    request_received = threading.Event()
    release_handler = threading.Event()

    class HeldResponseHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            request_received.set()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            self.wfile.flush()
            release_handler.wait(3)

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), HeldResponseHandler
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    client = _client(endpoint=f"http://127.0.0.1:{server.server_port}")
    request = _request("held-invoke")
    request.payload["stream"] = False
    results = []
    invoke_thread = threading.Thread(
        target=lambda: results.append(client.invoke(request))
    )
    try:
        invoke_thread.start()
        assert request_received.wait(2)
        deadline = time.monotonic() + 2
        attached = False
        while time.monotonic() < deadline:
            with client._active_requests_lock:
                record = client._active_requests.get("held-invoke")
                attached = record is not None and record.response is not None
            if attached:
                break
            time.sleep(0.005)
        assert attached
        started = time.monotonic()
        cancelled = client.cancel("held-invoke")
        assert time.monotonic() - started < 0.25
        assert cancelled.status is EnvelopeStatus.CANCELLED
        invoke_thread.join(2)
        assert not invoke_thread.is_alive()
        assert results[0].status is EnvelopeStatus.CANCELLED
        assert client._launcher.stop_calls == 0
    finally:
        release_handler.set()
        server.shutdown()
        server.server_close()
        server_thread.join(2)


def test_real_http_cancel_while_waiting_for_headers_is_request_scoped():
    held_request_received = threading.Event()
    release_held_headers = threading.Event()

    class DelayedHeadersHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            request = json.loads(body)
            message = request["messages"][0]["content"]
            if message == "hold":
                held_request_received.set()
                release_held_headers.wait(3)
            response_body = (
                b'{"choices":[{"message":{"content":"ok"},'
                b'"finish_reason":"stop"}]}'
            )
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), DelayedHeadersHandler
    )
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    client = _client(endpoint=f"http://127.0.0.1:{server.server_port}")
    held_request = _request("waiting-for-headers")
    held_request.payload["stream"] = False
    held_request.payload["messages"][0]["content"] = "hold"
    held_results = []
    held_thread = threading.Thread(
        target=lambda: held_results.append(client.invoke(held_request))
    )
    other_request = _request("other-request")
    other_request.payload["stream"] = False
    other_request.payload["messages"][0]["content"] = "other"
    other_results = []
    other_thread = threading.Thread(
        target=lambda: other_results.append(client.invoke(other_request))
    )
    try:
        held_thread.start()
        assert held_request_received.wait(2)
        with client._active_requests_lock:
            held_record = client._active_requests.get("waiting-for-headers")
            assert held_record is not None
            assert held_record.response is not None

        other_thread.start()
        other_thread.join(2)
        assert not other_thread.is_alive()
        assert other_results[0].status is EnvelopeStatus.SUCCEEDED

        started = time.monotonic()
        cancelled = client.cancel("waiting-for-headers")
        assert cancelled.status is EnvelopeStatus.CANCELLED
        assert time.monotonic() - started < 0.25
        held_thread.join(0.5)
        assert not held_thread.is_alive()
        assert held_results[0].status is EnvelopeStatus.CANCELLED
        assert client._launcher.stop_calls == 0
    finally:
        release_held_headers.set()
        held_thread.join(2)
        server.shutdown()
        server.server_close()
        server_thread.join(2)


def test_cancel_unknown_request_does_not_stop_server():
    client = _client()

    response = client.cancel("unknown")

    assert response.status is EnvelopeStatus.FAILED
    assert response.error.code == "llm_request_not_active"
    assert client._launcher.stop_calls == 0


def test_public_stream_frames_preserve_usage_and_failure_status():
    usage = {"prompt_tokens": 13, "completion_tokens": 4}
    final = StreamDelta(
        request_id="r",
        final=True,
        metadata={"usage": usage},
    )
    assert websocket_chunk(final)["usage"] == usage
    assert client_frame(final, "conversation")["usage"] == usage

    failure = StreamDelta(
        request_id="r",
        final=True,
        status=EnvelopeStatus.FAILED,
        metadata={"error": "truncated"},
    )
    assert websocket_chunk(failure)["type"] == "error"
    assert client_frame(failure, None)["type"] == "error"
