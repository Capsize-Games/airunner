# WebSocket Transport Architecture

## Overview

The WebSocket transport replaces HTTP polling with push-based messaging
for communication between the API server and sidecar runtime processes.
All four sidecar clients (Art, TTS, LLM, STT) now support WebSocket as
their primary transport, with HTTP as a backward-compatible fallback.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI API Server                            │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ ArtClient   │  │ TTSClient   │  │ LLMClient   │  │ STTClient│ │
│  │ (WS+HTTP)   │  │ (WS+HTTP)   │  │ (WS+HTTP)   │  │ (WS+HTTP)│ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬─────┘ │
│         │                │                │              │        │
│  ┌──────┴────────────────┴────────────────┴──────────────┴──────┐ │
│  │              SidecarWebSocketTransport                        │ │
│  │         shared async WS client (websocket_transport.py)       │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
                          │ WebSocket
                          ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Art Daemon  │  │ TTS Daemon  │  │LLM Adapter  │  │STT Adapter  │
│ /daemon/ws  │  │ /daemon/ws  │  │(ws→HTTP)    │  │(ws→HTTP)    │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ diffusers   │  │ TTS engine  │  │ llama.cpp   │  │ whisper.cpp │
│ (own code)  │  │ (own code)  │  │ (3rd party) │  │ (3rd party) │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

## Key Components

### 1. SidecarWebSocketTransport (`websocket_transport.py`)

Shared async WebSocket client used by all sidecar clients.

**Public API:**

| Method | Description |
|--------|-------------|
| `connect()` | Opens a WebSocket connection to the daemon |
| `invoke(envelope)` | Sends a `RequestEnvelope`, waits for `ResponseEnvelope` |
| `invoke_stream(envelope, on_progress)` | Sends a request, streams progress deltas via callback, returns final response |
| `close()` | Closes the connection and fails pending futures |

**Message correlation:** Uses `request_id` from the `RequestEnvelope` to
match responses to pending calls via `asyncio.Future` objects.

**Background reader:** A background `asyncio.Task` reads JSON frames
from the WebSocket and dispatches them to the correct pending future or
stream callback.

### 2. Daemon-Side WebSocket Endpoints

For daemon processes we control (Art, TTS), WebSocket endpoints are
added directly to the FastAPI server:

| File | Endpoint | Actions |
|------|----------|---------|
| `art_daemon_ws.py` | `/api/v1/art/daemon/ws` | `generate`, `cancel`, `status`, `unload` |
| `tts_daemon_ws.py` | `/api/v1/tts/daemon/ws` | `synthesize`, `load`, `unload`, `health`, `cancel` |

Each endpoint accepts `RequestEnvelope`-style JSON, pushes progress
messages during long-running operations, and sends a final
`ResponseEnvelope` on completion.

### 3. WebSocket-to-HTTP Adapters

For third-party daemon processes (llama.cpp, whisper.cpp), thin adapter
processes sit between the WebSocket transport and the daemon's HTTP API:

| File | Adapter For | Port Offset |
|------|-------------|-------------|
| `llm_ws_adapter.py` | llama.cpp (chat completion) | daemon port + 1000 |
| `stt_ws_adapter.py` | whisper.cpp (transcription) | daemon port + 1000 |

Adapters are standalone `asyncio` WebSocket servers that:
- Accept `invoke` requests via WebSocket
- Forward them to the daemon's HTTP API
- Stream responses back through WebSocket
- Adapters can be run standalone via `python -m airunner_services.runtimes.llm_ws_adapter`

## Protocol

### Request Format

Every message from the transport to a daemon endpoint follows the
`RequestEnvelope` structure:

```json
{
    "request_id": "abc123",
    "action": "invoke",
    "payload": { ... },
    "metadata": {}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | string | Correlation ID for matching responses |
| `action` | string | `invoke`, `cancel`, `load`, `unload`, `health`, `status` |
| `payload` | object | Action-specific parameters |
| `metadata` | object | Optional context metadata |

### Progress Push Messages

During long-running operations, the daemon pushes progress updates:

```json
{
    "type": "progress",
    "request_id": "abc123",
    "progress": 45.0,
    "phase": "processing",
    "status": "running"
}
```

### Response Format

Every request receives exactly one final response:

```json
{
    "request_id": "abc123",
    "status": "succeeded" | "failed" | "cancelled",
    "payload": { ... },
    "metadata": {},
    "error": { "code": "...", "message": "..." }
}
```

## Transport Selection

Each sidecar client selects its transport via a constructor parameter:

```python
# Default: WebSocket preferred, HTTP fallback
client = SidecarArtClient(use_websocket=True)

# Legacy: HTTP only
client = SidecarArtClient(use_websocket=False)
```

The `RuntimeDescriptor` is updated to reflect the active transport:
- `TransportKind.WEBSOCKET` when WebSocket is enabled
- `TransportKind.HTTP` when falling back

## Message Flow Comparison

### Before (HTTP Polling — Art Example)

```
API Server                  Art Daemon
    │                           │
    ├── POST /generate ────────►│
    │◄─── {"job_id": "j1"} ─────┤
    │                           │
    ├── GET /status/j1 ────────►│  (repeated every 100ms)
    │◄─── {"progress": 12} ─────┤
    ├── GET /status/j1 ────────►│
    │◄─── {"progress": 45} ─────┤
    │       ... ~300 requests   │
    ├── GET /status/j1 ────────►│
    │◄─── {"status": "done"} ───┤
    ├── GET /result/j1 ────────►│
    │◄─── [image bytes] ────────┤
```

### After (WebSocket Push — Art Example)

```
API Server                  Art Daemon
    │                           │
    ├── WS Connect ───────────►│
    │◄─── Accepted ─────────────┤
    │                           │
    ├── {"action":"invoke",...}►│
    │◄─── {"type":"progress",   │  (pushed when state changes)
    │       "progress": 12} ────┤
    │◄─── {"type":"progress",   │
    │       "progress": 45} ────┤
    │       ...                 │
    │◄─── {"status":"succeeded",│
    │       "payload": {...}} ──┤
```

## Error Handling

| Error | Transport Behavior | Client Fallback |
|-------|-------------------|-----------------|
| Connection refused | `WebSocketTransportError` | Retry with HTTP fallback |
| Connection lost mid-request | `WebSocketTransportDisconnected` | Fail pending futures, retry |
| Request timeout | `WebSocketTransportTimeout` | Fail with retryable error |
| Invalid JSON from daemon | Log warning, skip message | N/A |
| Adapter process crash | Connection closed | Next request falls back to HTTP |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMA_HOST` | `127.0.0.1` | LLM adapter target host |
| `LLAMA_PORT` | `8080` | LLM adapter target port |
| `LLM_ADAPTER_HOST` | `127.0.0.1` | LLM adapter listen host |
| `LLM_ADAPTER_PORT` | `9082` | LLM adapter listen port |
| `STT_ADAPTER_HOST` | `127.0.0.1` | STT adapter listen host |
| `STT_ADAPTER_PORT` | `9083` | STT adapter listen port |

### Art Daemon Settings

The art daemon WebSocket endpoint is at `/api/v1/art/daemon/ws` and
does not require additional configuration — it shares the same host and
port as the daemon's HTTP server.

## Migration Status

All four sidecar clients have been migrated:

| Sidecar | Client File | Daemon/Adapter File | Status |
|---------|-------------|---------------------|--------|
| Art | `sidecar_art_client.py` | `art_daemon_ws.py` | ✅ WebSocket + HTTP fallback |
| TTS | `sidecar_tts_client.py` | `tts_daemon_ws.py` | ✅ WebSocket + HTTP fallback |
| LLM | `sidecar_llm_client.py` | `llm_ws_adapter.py` | ✅ WebSocket + HTTP fallback |
| STT | `sidecar_stt_client.py` | `stt_ws_adapter.py` | ✅ WebSocket + HTTP fallback |
