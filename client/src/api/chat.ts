import { request } from "./client-base";
import { BASE_URL, type JsonObject, type Message } from "../types/api";

// ── Health / Daemon ──
export async function healthCheck() {
  return request<{ status: string }>("GET", "/api/v1/health");
}

export async function getHardwareProfile() {
  return request<import("../types/api").HardwareProfile>(
    "GET", "/api/v1/daemon/hardware",
  );
}

// ── Conversations ──
export async function listConversations(limit = 50) {
  return request<import("../types/api").ConversationListResponse>(
    "GET", `/api/v1/llm/conversations?limit=${limit}`,
  );
}

export async function createConversation() {
  return request<{ id: number }>("POST", "/api/v1/llm/conversations");
}

export async function deleteConversation(id: number) {
  return request<void>("DELETE", `/api/v1/llm/conversations/${id}`);
}

export async function loadConversation(conversationId: number) {
  return request<import("../types/api").ConversationSessionResponse>(
    "GET",
    `/api/v1/llm/conversations/session?conversation_id=${conversationId}`,
  );
}

export async function selectConversation(conversationId: number) {
  return request<import("../types/api").ConversationSessionResponse>(
    "POST",
    "/api/v1/llm/conversations/select",
    { conversation_id: conversationId },
  );
}

// ── LLM Models ──
export async function listLLMModels() {
  const data = await request<import("../types/api").BootstrapData>(
    "GET", "/api/v1/art/bootstrap",
  );
  const models = data.models ?? [];
  return models
    .filter((m: JsonObject) => m.category === "llm")
    .map((m: JsonObject) => ({
      label: String(m.name ?? m.version ?? m.path),
      value: String(m.path ?? ""),
      category: String(m.category ?? ""),
      pipeline_action: String(m.pipeline_action ?? ""),
    }));
}

// ---------------------------------------------------------------------------
// TTS — module-level singleton WebSocket for non-React callers
// ---------------------------------------------------------------------------

let _ttsWs: WebSocket | null = null;
let _ttsReady = false;
let _ttsPendingResolve: ((blob: Blob) => void) | null = null;
let _ttsPendingReject: ((err: Error) => void) | null = null;
let _ttsReconnectTimer: ReturnType<typeof setTimeout> | null = null;

import { wsHost } from "./client-base";

function _ttsWsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${wsHost()}/api/v1/tts/ws`;
}

function _ttsConnect(): void {
  if (_ttsWs) {
    _ttsWs.onclose = null;
    _ttsWs.onerror = null;
    _ttsWs.onmessage = null;
    _ttsWs.close();
    _ttsWs = null;
  }

  try {
    const socket = new WebSocket(_ttsWsUrl());
    _ttsWs = socket;

    socket.onopen = () => {
      _ttsReady = true;
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "audio") {
          const raw = data.data as string;
          const binary = atob(raw);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: "audio/wav" });
          if (_ttsPendingResolve) {
            _ttsPendingResolve(blob);
            _ttsPendingResolve = null;
            _ttsPendingReject = null;
          }
        } else if (data.type === "error") {
          const msg = data.message ?? "TTS failed";
          if (_ttsPendingReject) {
            _ttsPendingReject(new Error(msg));
            _ttsPendingResolve = null;
            _ttsPendingReject = null;
          }
        }
      } catch { /* ignore */ }
    };

    socket.onclose = (event) => {
      _ttsWs = null;
      _ttsReady = false;
      if (!event.wasClean) {
        _ttsReconnectTimer = setTimeout(_ttsConnect, 5000);
      }
    };

    socket.onerror = () => {
      socket.close();
    };
  } catch {
    _ttsReconnectTimer = setTimeout(_ttsConnect, 5000);
  }
}

function _ttsSend(msg: Record<string, unknown>): void {
  if (_ttsWs?.readyState === WebSocket.OPEN) {
    _ttsWs.send(JSON.stringify(msg));
  }
}

function _ttsDisconnect(): void {
  if (_ttsReconnectTimer) {
    clearTimeout(_ttsReconnectTimer);
    _ttsReconnectTimer = null;
  }
  if (_ttsWs) {
    _ttsWs.onclose = null;
    _ttsWs.onerror = null;
    _ttsWs.onmessage = null;
    _ttsWs.close();
    _ttsWs = null;
  }
  _ttsReady = false;
}

// Initialize TTS WebSocket connection eagerly (lazy on first call)
let _ttsInit = false;
function _ttsEnsureConnected(): void {
  if (!_ttsInit) {
    _ttsInit = true;
    _ttsConnect();
  }
}

export async function synthesizeTTS(
  text: string,
  voice?: string,
  speed = 1.0,
): Promise<Blob> {
  _ttsEnsureConnected();

  return new Promise((resolve, reject) => {
    _ttsPendingResolve = resolve;
    _ttsPendingReject = reject;

    _ttsSend({
      type: "synthesize",
      text,
      voice,
      speed,
    });
  });
}

// ── LLM Settings Presets ──
export async function listLLMPresets(): Promise<
  Array<{ label: string; args: Record<string, unknown> }>
> {
  const data = await request<{
    presets: Array<{ label: string; args: Record<string, unknown> }>;
  }>("GET", "/api/v1/llm/settings-presets");
  return Array.isArray(data) ? data : (data.presets ?? []);
}
