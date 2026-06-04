import { request } from "./client-base";

export async function getCanvasDocument(): Promise<{
  document: string | null;
}> {
  return request<{ document: string | null }>(
    "GET",
    "/api/v1/canvas/document",
  );
}

export async function saveCanvasDocument(
  document: string,
): Promise<void> {
  await request("PUT", "/api/v1/canvas/document", { document });
}
