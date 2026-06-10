import { useCallback } from "react";
import type { JsonObject } from "../types/api";

// ── useCivitaiDetailCache ─────────────────────────────────────────────────────
// No-op: previously cached Civitai model details in IndexedDB.
// Now always returns null; callers should fetch directly from server.

export function useCivitaiDetailCache() {
  const get = useCallback(async (_modelId: number): Promise<JsonObject | null> => {
    return null;
  }, []);

  return { get };
}
