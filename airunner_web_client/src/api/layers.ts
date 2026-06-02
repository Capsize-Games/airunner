import { request } from "./client-base";

export interface LayerInfo {
  id: number;
  name: string;
  visible: boolean;
  locked: boolean;
  order: number;
  opacity: number;
  blend_mode: string;
}

export async function listLayers() {
  return request<{ layers: LayerInfo[] }>("GET", "/api/v1/canvas/layers");
}

export async function createLayer() {
  return request<LayerInfo>("POST", "/api/v1/canvas/layers");
}

export async function updateLayer(
  layerId: number,
  props: Partial<Pick<LayerInfo, "visible" | "locked" | "name" | "opacity">>,
) {
  const params = new URLSearchParams();
  for (const [key, val] of Object.entries(props)) {
    if (val !== undefined) params.set(key, String(val));
  }
  return request<LayerInfo>(
    "PATCH",
    `/api/v1/canvas/layers/${layerId}?${params.toString()}`,
  );
}

export async function deleteLayer(layerId: number) {
  return request<{ status: string }>(
    "DELETE", `/api/v1/canvas/layers/${layerId}`,
  );
}

export async function moveLayer(layerId: number, direction: "up" | "down") {
  return request<{ status: string }>(
    "POST", `/api/v1/canvas/layers/${layerId}/move?direction=${direction}`,
  );
}

export async function mergeVisibleLayers() {
  return request<{ status: string; layer_id: number }>(
    "POST", "/api/v1/canvas/layers/merge-visible",
  );
}
