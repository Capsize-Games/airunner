import { request } from "./client-base";

export interface EmbeddingInfo {
  id: number;
  name: string;
  path: string;
  enabled: boolean;
  trigger_words: string[];
}

export async function listEmbeddings() {
  return request<{ embeddings: EmbeddingInfo[] }>(
    "GET", "/api/v1/art/embeddings",
  );
}

export async function updateEmbedding(
  embeddingId: number,
  props: { enabled?: boolean; trigger_words?: string },
) {
  return request<EmbeddingInfo>(
    "PATCH",
    `/api/v1/art/embeddings/${embeddingId}`,
    props as Record<string, unknown>,
  );
}
