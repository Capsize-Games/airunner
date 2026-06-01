import {
  BASE_URL,
  type JsonObject,
  type StreamChunk,
} from "../types/api";

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

async function requestBlob(
  method: string,
  path: string,
  body?: JsonObject,
): Promise<Blob> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.blob();
}

// ---------------------------------------------------------------------------
// Streaming helper (SSE / NDJSON)
// ---------------------------------------------------------------------------
async function* streamRequest(
  method: string,
  path: string,
  body?: JsonObject,
): AsyncGenerator<StreamChunk> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
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
      } catch {
        // skip unparseable line
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Health / Daemon
// ---------------------------------------------------------------------------
export async function healthCheck(): Promise<{ status: string }> {
  return request("GET", "/api/v1/health");
}

export async function getHardwareProfile() {
  return request<import("../types/api").HardwareProfile>(
    "GET",
    "/api/v1/daemon/hardware",
  );
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------
export async function listConversations(limit = 50) {
  return request<import("../types/api").ConversationListResponse>(
    "GET",
    `/api/v1/llm/conversations?limit=${limit}`,
  );
}

export async function createConversation() {
  return request<{ id: number }>("POST", "/api/v1/llm/conversations");
}

export async function getConversationSession(
  conversationId?: number,
  maxMessages = 50,
) {
  const query = conversationId
    ? `conversation_id=${conversationId}&max_messages=${maxMessages}`
    : `max_messages=${maxMessages}`;
  return request<import("../types/api").ConversationSessionResponse>(
    "GET",
    `/api/v1/llm/conversations/session?${query}`,
  );
}

export async function deleteConversation(id: number) {
  return request<void>("DELETE", `/api/v1/llm/conversations/${id}`);
}

// ---------------------------------------------------------------------------
// LLM Streaming
// ---------------------------------------------------------------------------
export async function* streamLLM(messages: import("../types/api").Message[]) {
  yield* streamRequest(
    "POST",
    "/api/v1/llm/conversations/stream",
    { messages },
  );
}

// ---------------------------------------------------------------------------
// Art
// ---------------------------------------------------------------------------
export async function startArtGeneration(
  params: import("../types/api").ArtGenerateRequest,
) {
  return request<import("../types/api").ArtGenerateResponse>(
    "POST",
    "/api/v1/art/generate",
    params as unknown as JsonObject,
  );
}

export async function getArtJobStatus(jobId: string) {
  return request<import("../types/api").ArtJobStatus>(
    "GET",
    `/api/v1/art/status/${jobId}`,
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
  return requestBlob("POST", "/api/v1/tts/synthesize", {
    text,
    voice,
    speed,
  } as unknown as JsonObject);
}

export async function transcribeAudio(
  audioBlob: Blob,
): Promise<{ text: string }> {
  const form = new FormData();
  form.append("audio", audioBlob, "audio.wav");
  const response = await fetch(`${BASE_URL}/api/v1/stt/transcribe`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Settings (resource store)
// ---------------------------------------------------------------------------
export async function getSingleton(
  resourceName: string,
): Promise<import("../types/api").ResourceRecord> {
  return request(
    "GET",
    `/api/v1/settings/resources/${resourceName}/singleton?create_if_missing=true`,
  );
}

export async function updateSingleton(
  resourceName: string,
  values: JsonObject,
): Promise<import("../types/api").ResourceRecord> {
  return request(
    "PUT",
    `/api/v1/settings/resources/${resourceName}/singleton`,
    { values },
  );
}

export async function queryResource(
  resourceName: string,
  filters?: JsonObject,
): Promise<{ records: import("../types/api").ResourceRecord[] }> {
  return request(
    "POST",
    `/api/v1/catalog/resources/${resourceName}/query`,
    { filters: filters ?? {} },
  );
}

// ---------------------------------------------------------------------------
// Catalog / Bootstrap
// ---------------------------------------------------------------------------
export async function getBootstrapData() {
  return request<import("../types/api").BootstrapData>(
    "GET",
    "/api/v1/art/bootstrap",
  );
}

// ---------------------------------------------------------------------------
// Downloads
// ---------------------------------------------------------------------------
export async function startHuggingFaceDownload(
  repoId: string,
  modelType = "llm",
) {
  return request<import("../types/api").DownloadJobAccepted>(
    "POST",
    "/api/v1/downloads/huggingface",
    { repo_id: repoId, model_type: modelType },
  );
}

export async function getDownloadJobStatus(jobId: string) {
  return request<import("../types/api").DownloadJobStatus>(
    "GET",
    `/api/v1/downloads/status/${jobId}`,
  );
}
