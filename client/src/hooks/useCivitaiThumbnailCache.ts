import { useCallback } from "react";
import { useDb } from "../db/DbContext";

// ── useCivitaiThumbnailCache ──────────────────────────────────────────────────
// Cache-miss-only strategy: once a thumbnail blob is stored it is never
// overwritten.  Keys are `${modelId}_${versionIndex}_${imageUrl}`.
// The blob field stores the full size-variant map as JSON so that the
// complete b64Map ({[size]: dataUrl}) can be recovered on cache hit.

export function useCivitaiThumbnailCache() {
  const db = useDb();

  // Store the full size-variant map for one (modelId, versionIndex, imageUrl).
  // b64Map is e.g. { "256": "data:image/...", "512": "data:image/..." }.
  const store = useCallback(async (
    modelId: number,
    versionIndex: number,
    imageUrl: string,
    b64Map: Record<string, string>,
  ): Promise<void> => {
    if (!db) return;
    const key = `${modelId}_${versionIndex}_${imageUrl}`;
    const serialized = JSON.stringify(b64Map);
    try {
      const existing = await db.civitaiThumbnails.get(key);
      if (existing) return; // cache-miss-only: skip if already stored
      await db.civitaiThumbnails.put({ key, blob: serialized, cachedAt: Date.now() });
    } catch {
      // Quota exceeded — evict oldest thumbnail batch and retry once.
      try {
        const evictCount = 20;
        const oldest = await db.civitaiThumbnails
          .orderBy("cachedAt")
          .limit(evictCount)
          .primaryKeys();
        await db.civitaiThumbnails.bulkDelete(oldest as string[]);
        await db.civitaiThumbnails.put({ key, blob: serialized, cachedAt: Date.now() });
      } catch { /* give up */ }
    }
  }, [db]);

  // Returns { [imageUrl]: b64Map } for all cached images in a version.
  const getAll = useCallback(async (
    modelId: number,
    versionIndex: number,
  ): Promise<Record<string, Record<string, string>>> => {
    if (!db) return {};
    try {
      const prefix = `${modelId}_${versionIndex}_`;
      const records = await db.civitaiThumbnails
        .where("key")
        .startsWith(prefix)
        .toArray();
      const out: Record<string, Record<string, string>> = {};
      for (const r of records) {
        const imageUrl = r.key.slice(prefix.length);
        try {
          out[imageUrl] = JSON.parse(r.blob) as Record<string, string>;
        } catch {
          // Legacy entry stored as a plain data URL — wrap it.
          out[imageUrl] = { "": r.blob };
        }
      }
      return out;
    } catch {
      return {};
    }
  }, [db]);

  return { store, getAll };
}
