import { useState, useEffect, useCallback } from "react";
import { useDb } from "../db/DbContext";
import { SyncManager } from "../db/SyncManager";
import type { EmbeddingInfo } from "../api/embeddings";
import type { CachedEmbedding } from "../db/db";

function toCached(e: EmbeddingInfo): CachedEmbedding {
  return { ...e, cachedAt: Date.now() };
}

// ── useEmbeddings ─────────────────────────────────────────────────────────────

export function useEmbeddings() {
  const db = useDb();
  const [embeddings, setEmbeddings] = useState<EmbeddingInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<CachedEmbedding[]> => {
    const { listEmbeddings } = await import("../api/client");
    const data = await listEmbeddings();
    return (data.embeddings ?? []).map(toCached);
  }, []);

  const sync = useCallback(async () => {
    if (!db) {
      try {
        const fresh = await serverFetch();
        setEmbeddings(fresh);
      } catch { /* unavailable */ } finally {
        setLoading(false);
      }
      return;
    }

    const manager = new SyncManager(db.embeddings, serverFetch, "embeddings");

    const cached = await manager.readCached();
    if (cached.length > 0) {
      setEmbeddings(cached);
      setLoading(false);
    }

    try {
      const merged = await manager.sync();
      setEmbeddings(merged);
    } catch { /* stale cache */ } finally {
      setLoading(false);
    }
  }, [db, serverFetch]);

  useEffect(() => {
    sync();
  }, [sync]);

  const patchEmbedding = useCallback(async (updated: EmbeddingInfo) => {
    setEmbeddings((prev) => prev.map((e) => e.id === updated.id ? updated : e));
    if (db) await db.embeddings.put(toCached(updated));
  }, [db]);

  return { embeddings, loading, sync, patchEmbedding };
}
