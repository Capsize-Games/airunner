import { useCallback } from "react";
import { useDb } from "../db/DbContext";

// ── useCivitaiThumbnailCache ──────────────────────────────────────────────────
// Cache-miss-only strategy: once a thumbnail blob is stored it is never
// overwritten.  Keys are `${modelId}_${versionIndex}_${imageUrl}`.

export function useCivitaiThumbnailCache() {
  const db = useDb();

  const store = useCallback(async (
    modelId: number,
    versionIndex: number,
    imageUrl: string,
    blob: string,        // base64 data URL
  ): Promise<void> => {
    if (!db) return;
    const key = `${modelId}_${versionIndex}_${imageUrl}`;
    try {
      const existing = await db.civitaiThumbnails.get(key);
      if (existing) return; // cache-miss-only: skip if already stored
      await db.civitaiThumbnails.put({ key, blob, cachedAt: Date.now() });
    } catch {
      // Quota exceeded — evict oldest thumbnail batch and retry once.
      try {
        const evictCount = 20;
        const oldest = await db.civitaiThumbnails
          .orderBy("cachedAt")
          .limit(evictCount)
          .primaryKeys();
        await db.civitaiThumbnails.bulkDelete(oldest as string[]);
        await db.civitaiThumbnails.put({ key, blob, cachedAt: Date.now() });
      } catch { /* give up */ }
    }
  }, [db]);

  const getAll = useCallback(async (
    modelId: number,
    versionIndex: number,
  ): Promise<Record<string, string>> => {
    if (!db) return {};
    try {
      const prefix = `${modelId}_${versionIndex}_`;
      const records = await db.civitaiThumbnails
        .where("key")
        .startsWith(prefix)
        .toArray();
      const out: Record<string, string> = {};
      for (const r of records) {
        const imageUrl = r.key.slice(prefix.length);
        out[imageUrl] = r.blob;
      }
      return out;
    } catch {
      return {};
    }
  }, [db]);

  return { store, getAll };
}
