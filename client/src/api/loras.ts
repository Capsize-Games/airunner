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
  const params = new URLSearchParams();
  if (props.enabled !== undefined) params.set("enabled", String(props.enabled));
  if (props.trigger_words !== undefined) params.set("trigger_words", props.trigger_words);
  if (props.weight !== undefined) params.set("weight", String(props.weight));
  return request<LoraInfo>(
    "PATCH", `/api/v1/art/loras/${loraId}?${params.toString()}`,
  );
}
