"""WebSocket-to-HTTP adapter for whisper.cpp sidecar.

This adapter runs as a thin subprocess alongside whisper.cpp and
provides a WebSocket endpoint that forwards transcription requests
to whisper.cpp's HTTP API.

The adapter listens on ``ws://{host}:{port}/ws``.

Protocol
--------
Request::
    {
        "request_id": "...",
        "action": "invoke" | "health",
        "payload": {
            "audio_b64": "...",  // base64-encoded WAV audio
            "mime_type": "audio/wav",
            "language": "auto"
        }
    }

Response::
    {
        "request_id": "...",
        "status": "succeeded" | "failed",
        "payload": {"text": "...", "language": "en"}
    }
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request as HTTPRequest
from urllib.request import urlopen
from uuid import uuid4

import websockets
from websockets.asyncio.server import serve as ws_serve
from websockets.asyncio.server import ServerConnection

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

_DEFAULT_WHISPER_HOST = "127.0.0.1"
_DEFAULT_WHISPER_PORT = 8081
_DEFAULT_ADAPTER_HOST = "127.0.0.1"
_DEFAULT_ADAPTER_PORT = 8083
_DEFAULT_HTTP_TIMEOUT = 120.0


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


class STTWebSocketAdapter:
    """Thin WebSocket-to-HTTP proxy for whisper.cpp.

    Receives audio via WebSocket (base64), forwards to whisper.cpp's
    HTTP inference endpoint, and returns the transcription.
    """

    def __init__(
        self,
        *,
        whisper_host: str = _DEFAULT_WHISPER_HOST,
        whisper_port: int = _DEFAULT_WHISPER_PORT,
        adapter_host: str = _DEFAULT_ADAPTER_HOST,
        adapter_port: int = _DEFAULT_ADAPTER_PORT,
        http_timeout: float = _DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        self._whisper_url = f"http://{whisper_host}:{whisper_port}/inference"
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
            "STT WebSocket adapter listening on "
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
        logger.info("STT adapter: client connected")
        try:
            async for raw in websocket:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "error": "Invalid JSON",
                            }
                        )
                    )
                    continue

                request_id = str(data.get("request_id", ""))
                action = str(data.get("action", "") or "")

                if action in ("invoke", "transcribe"):
                    await self._handle_transcribe(
                        websocket,
                        request_id,
                        data.get("payload", {}),
                    )
                elif action in ("health", "status"):
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "response",
                                "request_id": request_id,
                                "status": "succeeded",
                                "payload": {
                                    "status": "ready",
                                    "adapter": "stt_ws",
                                },
                            }
                        )
                    )
                else:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "response",
                                "request_id": request_id,
                                "status": "failed",
                                "error": f"Unknown action: {action}",
                            }
                        )
                    )
        except websockets.ConnectionClosed:
            logger.info("STT adapter: client disconnected")
        except Exception as exc:
            logger.error("STT adapter error: %s", exc)

    async def _handle_transcribe(
        self,
        websocket: ServerConnection,
        request_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Forward one transcription request to whisper.cpp."""
        audio_b64 = str(payload.get("audio_b64", "") or "")
        if not audio_b64:
            await websocket.send(
                json.dumps(
                    {
                        "type": "response",
                        "request_id": request_id,
                        "status": "failed",
                        "error": "No audio data provided",
                    }
                )
            )
            return

        try:
            audio_bytes = base64.b64decode(audio_b64, validate=True)
        except Exception:
            await websocket.send(
                json.dumps(
                    {
                        "type": "response",
                        "request_id": request_id,
                        "status": "failed",
                        "error": "Invalid base64 audio",
                    }
                )
            )
            return

        language = str(payload.get("language", "auto") or "auto")
        mime_type = str(payload.get("mime_type", "audio/wav") or "audio/wav")

        # Build multipart request for whisper.cpp
        boundary = f"airunner-ws-adapter-{uuid4().hex}"
        body = self._multipart_body(
            boundary,
            audio_bytes,
            language,
            mime_type,
        )

        result = await self._http_request(body, boundary)
        if result is None:
            await websocket.send(
                json.dumps(
                    {
                        "type": "response",
                        "request_id": request_id,
                        "status": "failed",
                        "error": "whisper.cpp request failed",
                    }
                )
            )
            return

        text = result.get("text") or result.get("transcription", "")
        detected_language = result.get("language", language)

        await websocket.send(
            json.dumps(
                {
                    "type": "response",
                    "request_id": request_id,
                    "status": "succeeded",
                    "payload": {
                        "text": str(text),
                        "language": detected_language,
                    },
                }
            )
        )

    def _multipart_body(
        self,
        boundary: str,
        audio_bytes: bytes,
        language: str,
        mime_type: str,
    ) -> bytes:
        """Build a multipart form body for whisper.cpp."""
        parts = [
            self._field(boundary, "response_format", "json").encode("utf-8"),
            self._field(boundary, "language", language).encode("utf-8"),
        ]
        parts.append(
            b"--" + boundary.encode("utf-8") + b"\r\n"
            b'Content-Disposition: form-data; name="file"; '
            b'filename="audio.wav"\r\n'
            b"Content-Type: "
            + mime_type.encode("utf-8")
            + b"\r\n\r\n"
            + audio_bytes
            + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        return b"".join(parts)

    @staticmethod
    def _field(boundary: str, name: str, value: str) -> str:
        """Return one multipart form field string."""
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )

    async def _http_request(
        self,
        body: bytes,
        boundary: str,
    ) -> Optional[dict[str, Any]]:
        """Send one multipart HTTP POST to whisper.cpp."""
        req = HTTPRequest(
            url=self._whisper_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": (f"multipart/form-data; boundary={boundary}"),
                "Accept": "application/json",
            },
        )
        loop = asyncio.get_event_loop()

        def _do_request():
            try:
                with urlopen(req, timeout=self._http_timeout) as resp:
                    return json.loads(resp.read().decode("utf-8") or "{}")
            except (HTTPError, URLError) as exc:
                logger.error("whisper.cpp HTTP error: %s", exc)
                return None

        return await loop.run_in_executor(None, _do_request)


async def run_adapter() -> None:
    """Entry point: parse env vars and start the adapter."""
    adapter = STTWebSocketAdapter(
        whisper_host=_env_str("WHISPER_HOST", _DEFAULT_WHISPER_HOST),
        whisper_port=_env_int("WHISPER_PORT", _DEFAULT_WHISPER_PORT),
        adapter_host=_env_str(
            "STT_ADAPTER_HOST",
            _DEFAULT_ADAPTER_HOST,
        ),
        adapter_port=_env_int(
            "STT_ADAPTER_PORT",
            _DEFAULT_ADAPTER_PORT,
        ),
        http_timeout=_env_int(
            "STT_HTTP_TIMEOUT",
            int(_DEFAULT_HTTP_TIMEOUT),
        ),
    )
    await adapter.start()
    logger.info("STT WebSocket adapter started")

    try:
        await asyncio.Future()  # run forever
    except KeyboardInterrupt:
        pass
    finally:
        await adapter.stop()


if __name__ == "__main__":
    asyncio.run(run_adapter())
