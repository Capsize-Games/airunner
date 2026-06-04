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
  const params = new URLSearchParams();
  if (props.enabled !== undefined) params.set("enabled", String(props.enabled));
  if (props.trigger_words !== undefined) params.set("trigger_words", props.trigger_words);
  return request<EmbeddingInfo>(
    "PATCH", `/api/v1/art/embeddings/${embeddingId}?${params.toString()}`,
  );
}
