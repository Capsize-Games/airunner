import { request } from "./client-base";
import type { JsonObject } from "../types/api";

export interface ArtVersionInfo {
  name: string;
  models: { label: string; value: string }[];
  schedulers: { label: string; value: string }[];
}

export interface ArtOptionsResponse {
  versions: ArtVersionInfo[];
  precisions: { label: string; value: string }[];
}

export async function getArtModelOptions(): Promise<ArtOptionsResponse> {
  return request<ArtOptionsResponse>("GET", "/api/v1/art/options");
}

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

export async function getBootstrap() {
  return request<import("../types/api").BootstrapData>(
    "GET", "/api/v1/art/bootstrap",
  );
}

export interface SavedPrompt {
  id: number;
  prompt: string;
  secondary_prompt: string;
  negative_prompt: string;
  secondary_negative_prompt: string;
}

export async function listSavedPrompts(): Promise<{ prompts: SavedPrompt[] }> {
  return request<{ prompts: SavedPrompt[] }>("GET", "/api/v1/art/saved-prompts");
}

export async function createSavedPrompt(
  data: Omit<SavedPrompt, "id">,
): Promise<SavedPrompt> {
  return request<SavedPrompt>(
    "POST", "/api/v1/art/saved-prompts", data as unknown as JsonObject,
  );
}

export async function deleteSavedPrompt(id: number): Promise<void> {
  await request<void>("DELETE", `/api/v1/art/saved-prompts/${id}`);
}
