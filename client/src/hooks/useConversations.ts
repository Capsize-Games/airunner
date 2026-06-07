import { useState, useEffect, useCallback } from "react";
import { useDb } from "../db/DbContext";
import { SyncManager } from "../db/SyncManager";
import type { Conversation } from "../types/api";
import type { CachedConversation } from "../db/db";

function toCached(c: Conversation): CachedConversation {
  return { ...c, messages: undefined, cachedAt: Date.now() };
}

// ── useConversations ──────────────────────────────────────────────────────────
// Serves the conversation list from IndexedDB immediately; syncs with the
// server in the background.  Falls back to server-only when db is null.

export function useConversations() {
  const db = useDb();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<CachedConversation[]> => {
    const { listConversations } = await import("../api/client");
    const data = await listConversations(50);
    return (data.conversations ?? []).map(toCached);
  }, []);

  const refresh = useCallback(async () => {
    if (!db) {
      // No IndexedDB — fetch directly.
      try {
        const fresh = await serverFetch();
        setConversations(fresh);
      } catch {
        /* daemon unavailable */
      } finally {
        setLoading(false);
      }
      return;
    }

    const manager = new SyncManager(db.conversations, serverFetch, "conversations");

    // Serve cache immediately.
    const cached = await manager.readCached();
    if (cached.length > 0) {
      setConversations(cached);
      setLoading(false);
    }

    // Sync in background.
    try {
      const merged = await manager.sync();
      setConversations(merged);
    } catch {
      /* network unavailable — use stale cache */
    } finally {
      setLoading(false);
    }
  }, [db, serverFetch]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const remove = useCallback(async (id: number) => {
    const { deleteConversation } = await import("../api/client");
    await deleteConversation(id);
    if (db) await db.conversations.delete(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  }, [db]);

  const invalidateAndRefresh = useCallback(async () => {
    if (db) {
      const manager = new SyncManager(db.conversations, serverFetch, "conversations");
      await manager.invalidate();
    }
    await refresh();
  }, [db, serverFetch, refresh]);

  return { conversations, loading, refresh, remove, invalidateAndRefresh };
}
