import { request } from "./client-base";

export interface LoraInfo {
  id: number;
  name: string;
  path: string;
  enabled: boolean;
  trigger_words: string[];
  weight: number;
}

export async function listLoras() {
  return request<{ loras: LoraInfo[] }>(
    "GET", "/api/v1/art/loras",
  );
}

export async function updateLora(
  loraId: number,
  props: { enabled?: boolean; trigger_words?: string; weight?: number },
) {
  return request<LoraInfo>(
    "PATCH", `/api/v1/art/loras/${loraId}`, props as Record<string, unknown>,
  );
}
