import { useState, useEffect, useCallback } from "react";
import { useDb } from "../db/DbContext";
import { SyncManager } from "../db/SyncManager";
import type { LoraInfo } from "../api/loras";
import type { CachedLora } from "../db/db";

function toCached(l: LoraInfo): CachedLora {
  return { ...l, cachedAt: Date.now() };
}

// ── useLoras ──────────────────────────────────────────────────────────────────
// Serves the LoRA list from IndexedDB immediately; background-syncs from the
// server.  Falls back to server-only when db is null.
// On EVENT_LORAS: call sync() (delta-capable) rather than a full reload.

export function useLoras() {
  const db = useDb();
  const [loras, setLoras] = useState<LoraInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<CachedLora[]> => {
    const { listLoras } = await import("../api/client");
    const data = await listLoras();
    return (data.loras ?? []).map(toCached);
  }, []);

  const sync = useCallback(async () => {
    if (!db) {
      try {
        const fresh = await serverFetch();
        setLoras(fresh);
      } catch { /* unavailable */ } finally {
        setLoading(false);
      }
      return;
    }

    const manager = new SyncManager(db.loras, serverFetch, "loras");

    const cached = await manager.readCached();
    if (cached.length > 0) {
      setLoras(cached);
      setLoading(false);
    }

    try {
      const merged = await manager.sync();
      setLoras(merged);
    } catch { /* stale cache */ } finally {
      setLoading(false);
    }
  }, [db, serverFetch]);

  useEffect(() => {
    sync();
  }, [sync]);

  // Optimistic update: patch a single item in both state and IndexedDB.
  const patchLora = useCallback(async (updated: LoraInfo) => {
    setLoras((prev) => prev.map((l) => l.id === updated.id ? updated : l));
    if (db) await db.loras.put(toCached(updated));
  }, [db]);

  return { loras, loading, sync, patchLora };
}
