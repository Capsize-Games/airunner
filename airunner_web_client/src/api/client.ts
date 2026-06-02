import { BASE_URL, type JsonObject, type StreamChunk } from "../types/api";

// ---------------------------------------------------------------------------
// Generic fetch wrapper
// ---------------------------------------------------------------------------
async function request<T>(
  method: string,
  path: string,
  body?: JsonObject,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Streaming helper (SSE / NDJSON)
// ---------------------------------------------------------------------------
async function* streamRequest(
  method: string,
  path: string,
  body?: JsonObject,
  signal?: AbortSignal,
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const json = line.slice(6);
      try {
        yield JSON.parse(json) as StreamChunk;
      } catch { /* skip */ }
    }
  }
}

// ---------------------------------------------------------------------------
// Health / Daemon
// ---------------------------------------------------------------------------
export async function healthCheck() {
  return request<{ status: string }>("GET", "/api/v1/health");
}

export async function getHardwareProfile() {
  return request<import("../types/api").HardwareProfile>(
    "GET", "/api/v1/daemon/hardware",
  );
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// LLM Streaming
// ---------------------------------------------------------------------------
export async function* streamLLM(
  messages: import("../types/api").Message[],
  signal?: AbortSignal,
  model?: string,
  llmOverrides?: Record<string, Record<string, unknown>>,
) {
  yield* streamRequest(
    "POST", "/api/v1/llm/conversations/stream",
    { messages, model, stream: true, llm_overrides: llmOverrides },
    signal,
  );
}

// ---------------------------------------------------------------------------
// LLM Models (from catalog bootstrap)
// ---------------------------------------------------------------------------
export async function listLLMModels() {
  const data = await request<import("../types/api").BootstrapData>(
    "GET", "/api/v1/art/bootstrap",
  );
  const models = data.models ?? [];
  // Return LLM models with name as label, path as value
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
// Art
// ---------------------------------------------------------------------------
export async function startArtGeneration(
  params: import("../types/api").ArtGenerateRequest,
) {
  return request<import("../types/api").ArtGenerateResponse>(
    "POST", "/api/v1/art/generate", params as unknown as JsonObject,
  );
}

export async function getArtJobStatus(jobId: string) {
  return request<import("../types/api").ArtJobStatus>(
    "GET", `/api/v1/art/status/${jobId}`,
  );
}

// ---------------------------------------------------------------------------
// TTS / STT
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// LLM Settings Presets
// ---------------------------------------------------------------------------
export async function listLLMPresets() {
  return request<Array<{
    label: string;
    args: Record<string, unknown>;
  }>>("GET", "/api/v1/llm/settings-presets");
}

// ---------------------------------------------------------------------------
// Settings (resource store)
// ---------------------------------------------------------------------------
export async function getSingleton(resourceName: string) {
  const data = await request<{ record?: import("../types/api").ResourceRecord }>(
    "GET",
    `/api/v1/settings/resources/${resourceName}/singleton?create_if_missing=true`,
  );
  return (data.record ?? {}) as import("../types/api").ResourceRecord;
}

export async function updateSingleton(
  resourceName: string, values: JsonObject,
) {
  return request<import("../types/api").ResourceRecord>(
    "PUT", `/api/v1/settings/resources/${resourceName}/singleton`, { values },
  );
}

// ---------------------------------------------------------------------------
// Bootstrap (catalog metadata from services)
// ---------------------------------------------------------------------------
export async function getBootstrap() {
  return request<import("../types/api").BootstrapData>(
    "GET", "/api/v1/art/bootstrap",
  );
}

// ---------------------------------------------------------------------------
// Art options (schedulers, precisions from services enums)
// NOTE: Requires services endpoint GET /api/v1/art/options to be implemented.
// Falls back to empty lists when the endpoint is unavailable.
// ---------------------------------------------------------------------------
export interface ArtOptionsResponse {
  schedulers: { label: string; value: string }[];
  precisions: { label: string; value: string }[];
}

export async function getArtOptions(): Promise<ArtOptionsResponse> {
  try {
    return await request<ArtOptionsResponse>("GET", "/api/v1/art/options");
  } catch {
    return { schedulers: [], precisions: [] };
  }
}

// ---------------------------------------------------------------------------
// Knowledge Base
// ---------------------------------------------------------------------------
export async function listKnowledgeBaseDocuments() {
  return request<{ documents: import("../types/api").DocumentRecord[] }>(
    "GET", "/api/v1/knowledge-base/documents",
  );
}

// ---------------------------------------------------------------------------
// Downloads
// ---------------------------------------------------------------------------
export async function startHuggingFaceDownload(
  repoId: string, modelType = "llm",
) {
  return request<import("../types/api").DownloadJobAccepted>(
    "POST", "/api/v1/downloads/huggingface",
    { repo_id: repoId, model_type: modelType },
  );
}
