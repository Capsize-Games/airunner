/** Download-related API calls for CivitAI browser and file downloads. */

import { request } from "./client-base";
import type { JsonObject } from "../types/api";

// ── CivitAI search ──

export interface CivitaiSearchParams {
  query?: string;
  base_models?: string[];
  model_types?: string[];
  limit?: number;
  cursor?: string | null;
  api_key?: string;
}

export interface CivitaiModelInfoParams {
  model_id: string;
  base_models?: string[];
  model_types?: string[];
  api_key?: string;
}

export interface CivitaiFileDownloadParams {
  url: string;
  output_path: string;
  file_size?: number;
  api_key?: string;
  base_model?: string;
  model_type?: string;
}

export interface CivitaiImageParams {
  url: string;
  max_bytes?: number;
}

export interface CivitaiModelInfoByUrlParams {
  url: string;
  api_key?: string;
}

export async function searchCivitaiModels(
  params: CivitaiSearchParams,
): Promise<JsonObject> {
  return request<JsonObject>("POST", "/api/v1/downloads/civitai/models", {
    query: params.query ?? "",
    base_models: params.base_models ?? null,
    model_types: params.model_types ?? null,
    limit: params.limit ?? 20,
    cursor: params.cursor ?? null,
    api_key: params.api_key ?? "",
  });
}

export async function fetchCivitaiModel(
  params: CivitaiModelInfoParams,
): Promise<JsonObject> {
  return request<JsonObject>("POST", "/api/v1/downloads/civitai/model", {
    model_id: params.model_id,
    base_models: params.base_models ?? null,
    model_types: params.model_types ?? null,
    api_key: params.api_key ?? "",
  });
}

export async function startCivitaiFileDownload(
  params: CivitaiFileDownloadParams,
): Promise<{ job_id: string; status?: string }> {
  return request<{ job_id: string; status?: string }>(
    "POST",
    "/api/v1/downloads/civitai/file",
    {
      url: params.url,
      output_path: params.output_path,
      file_size: params.file_size ?? 0,
      api_key: params.api_key ?? "",
      base_model: params.base_model ?? null,
      model_type: params.model_type ?? null,
    },
  );
}

export async function fetchCivitaiModelByUrl(
  params: CivitaiModelInfoByUrlParams,
): Promise<JsonObject> {
  return request<JsonObject>("POST", "/api/v1/downloads/civitai/info", {
    url: params.url,
    api_key: params.api_key ?? "",
  });
}

// ── Download job management ──

export async function getDownloadJobStatus(
  jobId: string,
): Promise<{
  job_id: string;
  status: string;
  progress: number;
  error?: string;
  result?: JsonObject;
  metadata?: JsonObject;
}> {
  return request("GET", `/api/v1/downloads/status/${jobId}`);
}

export async function cancelDownloadJob(
  jobId: string,
): Promise<{ job_id: string; status?: string }> {
  return request("DELETE", `/api/v1/downloads/cancel/${jobId}`);
}

export async function requestCivitaiVersionThumbnails(params: {
  model_data: object;
  version_index: number;
}): Promise<void> {
  await request("POST", "/api/v1/downloads/civitai/version-thumbnails", params);
}

export async function cancelCivitaiVersionThumbnails(modelId: number): Promise<void> {
  await request("DELETE", "/api/v1/downloads/civitai/version-thumbnails", { model_id: modelId });
}
