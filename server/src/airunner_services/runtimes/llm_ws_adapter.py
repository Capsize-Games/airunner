"""WebSocket-to-HTTP adapter for llama.cpp sidecar.

This adapter runs as a thin subprocess alongside llama.cpp and provides
a WebSocket endpoint that forwards chat completion requests to llama.cpp's
OpenAI-compatible HTTP API and streams token deltas back to the caller.

The adapter listens on ``ws://{host}:{port}/ws`` and speaks the same
envelope protocol used by the art and TTS daemon WebSocket endpoints.

Protocol
--------
Request::
    {
        "request_id": "...",
        "action": "invoke" | "health",
        "payload": {
            "messages": [...],
            "stream": true|false,
            "temperature": 0.7,
            "max_tokens": null
        }
    }

Stream delta (for stream=true)::
    {
        "type": "stream",
        "request_id": "...",
        "sequence": 0,
        "delta": {"content": "Hello"},
        "final": false
    }

Final response (for stream=false or after stream completes)::
    {
        "request_id": "...",
        "status": "succeeded"|"failed",
        "payload": {"content": "...", "usage": {...}}
    }
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request as HTTPRequest
from urllib.request import urlopen

import websockets
from websockets.asyncio.server import serve as ws_serve
from websockets.asyncio.server import ServerConnection

from airunner_services.ipc.messages import EnvelopeStatus
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

_DEFAULT_LLAMA_HOST = "127.0.0.1"
_DEFAULT_LLAMA_PORT = 8080
_DEFAULT_ADAPTER_HOST = "127.0.0.1"
_DEFAULT_ADAPTER_PORT = 8082
_DEFAULT_HTTP_TIMEOUT = 120.0


def _env_str(name: str, default: str) -> str:
    """Return a string environment override when one is available."""
    return os.environ.get(name, default).strip() or default


def _env_int(name: str, default: int) -> int:
    """Return an integer environment override when one is available."""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


class LLMWebSocketAdapter:
    """Thin WebSocket-to-HTTP proxy for llama.cpp.

    Listens on a WebSocket port and forwards each request to
    llama.cpp's HTTP ``/v1/chat/completions`` endpoint.
    """

    def __init__(
        self,
        *,
        llama_host: str = _DEFAULT_LLAMA_HOST,
        llama_port: int = _DEFAULT_LLAMA_PORT,
        adapter_host: str = _DEFAULT_ADAPTER_HOST,
        adapter_port: int = _DEFAULT_ADAPTER_PORT,
        http_timeout: float = _DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        self._llama_url = (
            f"http://{llama_host}:{llama_port}/v1/chat/completions"
        )
        self._adapter_host = adapter_host
        self._adapter_port = adapter_port
        self._http_timeout = http_timeout
        self._server: Any = None

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._server = await ws_serve(
            self._handle_connection,
            self._adapter_host,
            self._adapter_port,
        )
        logger.info(
            "LLM WebSocket adapter listening on "
            f"ws://{self._adapter_host}:{self._adapter_port}/ws"
        )

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_connection(
        self,
        websocket: ServerConnection,
    ) -> None:
        """Handle one WebSocket connection."""
        logger.info("LLM adapter: client connected")
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "error": "Invalid JSON",
                    }))
                    continue

                request_id = str(data.get("request_id", ""))
                action = str(data.get("action", "") or "")

                if action == "invoke":
                    await self._handle_invoke(
                        websocket, request_id, data.get("payload", {}),
                    )
                elif action in ("health", "status"):
                    await self._handle_health(websocket, request_id)
                else:
                    await websocket.send(json.dumps({
                        "type": "response",
                        "request_id": request_id,
                        "status": "failed",
                        "error": f"Unknown action: {action}",
                    }))
        except websockets.ConnectionClosed:
            logger.info("LLM adapter: client disconnected")
        except Exception as exc:
            logger.error("LLM adapter error: %s", exc)

    async def _handle_invoke(
        self,
        websocket: ServerConnection,
        request_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Forward one chat completion request to llama.cpp."""
        stream = bool(payload.get("stream", False))

        body = {
            "messages": payload.get("messages", []),
            "stream": stream,
            "temperature": payload.get("temperature", 0.7),
        }
        if payload.get("max_tokens") is not None:
            body["max_tokens"] = payload["max_tokens"]
        if payload.get("model"):
            body["model"] = payload["model"]
        if payload.get("tool_choice"):
            body["tool_choice"] = payload["tool_choice"]

        if stream:
            await self._forward_stream(
                websocket, request_id, body,
            )
        else:
            await self._forward_sync(
                websocket, request_id, body,
            )

    async def _forward_sync(
        self,
        websocket: ServerConnection,
        request_id: str,
        body: dict[str, Any],
    ) -> None:
        """Forward one non-streaming request and return the response."""
        result = await self._http_request(body)
        if result is None:
            await websocket.send(json.dumps({
                "type": "response",
                "request_id": request_id,
                "status": "failed",
                "error": "llama.cpp request failed",
            }))
            return

        choices = result.get("choices") or [{}]
        message = choices[0].get("message") or {}
        await websocket.send(json.dumps({
            "type": "response",
            "request_id": request_id,
            "status": "succeeded",
            "payload": {
                "content": message.get("content", "") or "",
                "tools": message.get("tool_calls") or [],
                "usage": result.get("usage", {}),
            },
        }))

    async def _forward_stream(
        self,
        websocket: ServerConnection,
        request_id: str,
        body: dict[str, Any],
    ) -> None:
        """Forward one streaming request and send deltas via WebSocket."""
        response = await self._http_request_raw(body)
        if response is None:
            await websocket.send(json.dumps({
                "type": "response",
                "request_id": request_id,
                "status": "failed",
                "error": "llama.cpp streaming request failed",
            }))
            return

        sequence = 0
        final_content = ""
        try:
            while True:
                line = response.readline()
                if not line:
                    break
                if not line.startswith(b"data:"):
                    continue
                payload = line.split(b":", 1)[1].strip()
                if payload == b"[DONE]":
                    await websocket.send(json.dumps({
                        "type": "stream",
                        "request_id": request_id,
                        "sequence": sequence,
                        "delta": {},
                        "final": True,
                    }))
                    break

                data = json.loads(payload.decode("utf-8"))
                choice = (data.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                finish_reason = choice.get("finish_reason")
                chunk = {}
                if delta.get("content"):
                    chunk["content"] = delta["content"]
                    final_content += delta["content"]
                if delta.get("tool_calls"):
                    chunk["tool_calls"] = delta["tool_calls"]

                await websocket.send(json.dumps({
                    "type": "stream",
                    "request_id": request_id,
                    "sequence": sequence,
                    "delta": chunk,
                    "final": finish_reason is not None,
                }))
                sequence += 1

                if finish_reason is not None:
                    break
        finally:
            response.close()

    async def _handle_health(
        self,
        websocket: ServerConnection,
        request_id: str,
    ) -> None:
        """Return the adapter health status."""
        await websocket.send(json.dumps({
            "type": "response",
            "request_id": request_id,
            "status": "succeeded",
            "payload": {"status": "ready", "adapter": "llm_ws"},
        }))

    async def _http_request(
        self,
        body: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Send one HTTP POST to llama.cpp and return parsed JSON."""
        raw = await self._http_request_raw(body)
        if raw is None:
            return None
        try:
            return json.loads(raw.read().decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return None
        finally:
            raw.close()

    async def _http_request_raw(
        self,
        body: dict[str, Any],
    ) -> Any:
        """Send one HTTP POST to llama.cpp and return the response stream."""
        encoded = json.dumps(body).encode("utf-8")
        req = HTTPRequest(
            url=self._llama_url,
            data=encoded,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        loop = asyncio.get_event_loop()

        def _do_request():
            try:
                return urlopen(req, timeout=self._http_timeout)
            except (HTTPError, URLError) as exc:
                logger.error("llama.cpp HTTP error: %s", exc)
                return None

        return await loop.run_in_executor(None, _do_request)


async def run_adapter() -> None:
    """Entry point: parse env vars and start the adapter."""
    adapter = LLMWebSocketAdapter(
        llama_host=_env_str("LLAMA_HOST", _DEFAULT_LLAMA_HOST),
        llama_port=_env_int("LLAMA_PORT", _DEFAULT_LLAMA_PORT),
        adapter_host=_env_str(
            "LLM_ADAPTER_HOST", _DEFAULT_ADAPTER_HOST,
        ),
        adapter_port=_env_int(
            "LLM_ADAPTER_PORT", _DEFAULT_ADAPTER_PORT,
        ),
        http_timeout=_env_int(
            "LLM_HTTP_TIMEOUT", int(_DEFAULT_HTTP_TIMEOUT),
        ),
    )
    await adapter.start()
    logger.info("LLM WebSocket adapter started")

    # Keep running until interrupted
    try:
        await asyncio.Future()  # run forever
    except KeyboardInterrupt:
        pass
    finally:
        await adapter.stop()


if __name__ == "__main__":
    asyncio.run(run_adapter())
