// Re-exports from domain modules for backward compatibility.
// Prefer importing from the specific domain modules for new code.
import { BASE_URL, type JsonObject, type StreamChunk } from "../types/api";

export { BASE_URL, type JsonObject, type StreamChunk };

// Re-export shared helpers from client
export { request } from "./client-base";

// Re-export from domain modules
export * from "./canvas";
export * from "./chat";
export * from "./art";
export * from "./layers";
export * from "./embeddings";
export * from "./loras";
export * from "./images";
export * from "./settings";

// ── Model Status ──
export interface ActiveModelInfo {
  model_id: string;
  model_type: string;
  status: string;
  can_unload: boolean;
  vram_gb: number;
  ram_gb: number;
  name?: string;
}

export interface ActiveModelsResponse {
  models: ActiveModelInfo[];
}

export async function listActiveModels(): Promise<ActiveModelsResponse> {
  const { request } = await import("./client-base");
  return request<ActiveModelsResponse>("GET", "/api/v1/models/active");
}

export async function unloadModel(
  modelId: string,
  modelType: string,
): Promise<{ status: string; message: string }> {
  const { request } = await import("./client-base");
  return request<{ status: string; message: string }>(
    "POST",
    "/api/v1/models/unload",
    { model_id: modelId, model_type: modelType },
  );
}

export async function loadModel(
  modelId: string,
  modelType: string,
): Promise<{ status: string; message: string }> {
  const { request } = await import("./client-base");
  return request<{ status: string; message: string }>(
    "POST",
    "/api/v1/models/load",
    { model_id: modelId, model_type: modelType },
  );
}
