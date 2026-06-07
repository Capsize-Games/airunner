import { useCallback } from "react";
import { useDb } from "../db/DbContext";
import type { JsonObject } from "../types/api";

const TTL_MS = 72 * 60 * 60 * 1000; // 72 hours — matches server cache lifetime

// ── useCivitaiDetailCache ─────────────────────────────────────────────────────
// Replaces the in-memory `detailCache` ref in CivitaiBrowserPanel.
// Reads from IndexedDB first; falls back to server fetch on miss.
// Server returns permanent/long-lived data for model details, so we treat
// cached entries as valid for 72 h (same TTL the server applies).

export function useCivitaiDetailCache() {
  const db = useDb();

  const get = useCallback(async (modelId: number): Promise<JsonObject | null> => {
    if (!db) return null;
    try {
      const record = await db.civitaiModels.get(modelId);
      if (!record) return null;
      if (Date.now() - record.cachedAt > TTL_MS) {
        await db.civitaiModels.delete(modelId);
        return null;
      }
      return record.data as JsonObject;
    } catch {
      return null;
    }
  }, [db]);

  const set = useCallback(async (modelId: number, data: JsonObject): Promise<void> => {
    if (!db) return;
    try {
      await db.civitaiModels.put({ id: modelId, data: data as Record<string, unknown>, cachedAt: Date.now() });
    } catch {
      // Quota exceeded — evict oldest entry and retry once.
      try {
        const oldest = await db.civitaiModels.orderBy("cachedAt").first();
        if (oldest) await db.civitaiModels.delete(oldest.id);
        await db.civitaiModels.put({ id: modelId, data: data as Record<string, unknown>, cachedAt: Date.now() });
      } catch { /* give up */ }
    }
  }, [db]);

  return { get, set };
}
