import { getDb } from "./db";

// Eviction order — most expendable first.
// kbDocuments is last because KB data is harder to re-fetch than image caches.
// Never evict: conversations, messages, canvasDocuments.
const EVICTION_ORDER = [
  "civitaiThumbnails",
  "civitaiModels",
  "images",
  "imageDates",
  "loras",
  "embeddings",
  "kbDocuments",
] as const;

const EVICT_BATCH = 30;

/**
 * Attempt to reclaim space by removing the oldest entries from low-priority
 * tables.  Sweeps one batch per table in eviction order, stopping as soon as
 * `action` succeeds.
 */
export async function withQuotaEviction(
  action: () => Promise<void>,
): Promise<void> {
  try {
    await action();
    return;
  } catch (err) {
    if (!(err instanceof DOMException) || err.name !== "QuotaExceededError") {
      throw err;
    }
  }

  const db = getDb();
  if (!db) return;

  for (const tableName of EVICTION_ORDER) {
    try {
      const table = db[tableName] as import("dexie").Table;
      const keys = await table.orderBy("cachedAt").limit(EVICT_BATCH).primaryKeys();
      if (keys.length > 0) await table.bulkDelete(keys as never[]);
      await action();
      return;
    } catch {
      // Continue to next table.
    }
  }
}

/**
 * Clear all cached data from every evictable table and remove all sync
 * timestamps from localStorage.  Preserves conversations, messages, and
 * canvas state.
 */
export async function clearAllCache(): Promise<void> {
  const db = getDb();
  if (!db) return;

  await Promise.allSettled([
    db.civitaiThumbnails.clear(),
    db.civitaiModels.clear(),
    db.images.clear(),
    db.imageDates.clear(),
    db.loras.clear(),
    db.embeddings.clear(),
    db.kbDocuments.clear(),
  ]);

  // Remove sync timestamps.
  const syncKeys = Object.keys(localStorage).filter((k) =>
    k.startsWith("airunner:sync:"),
  );
  syncKeys.forEach((k) => {
    try { localStorage.removeItem(k); } catch { /* */ }
  });
}
