import { request, streamRequest } from "./client-base";
import { BASE_URL, type JsonObject, type StreamChunk, type Message } from "../types/api";

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

// ── LLM Streaming ──
export async function* streamLLM(
  messages: Message[],
  signal?: AbortSignal,
  model?: string,
  llmOverrides?: Record<string, Record<string, unknown>>,
  activeDocumentIds?: number[],
) {
  yield* streamRequest(
    "POST", "/api/v1/llm/conversations/stream",
    {
      messages,
      model,
      stream: true,
      llm_overrides: llmOverrides,
      active_document_ids: activeDocumentIds,
    },
    signal,
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

// ── TTS ──
export async function synthesizeTTS(
  text: string,
  voice?: string,
  speed = 1.0,
): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/api/v1/tts/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice, speed }),
  });
  if (!response.ok) throw new Error(`${response.status}`);
  return response.blob();
}

// ── LLM Settings Presets ──
export async function listLLMPresets() {
  return request<Array<{
    label: string;
    args: Record<string, unknown>;
  }>>("GET", "/api/v1/llm/settings-presets");
}
