import { useState, useEffect, useCallback, useRef } from "react";
import type { Conversation } from "../types/api";
import {
  loadConversationsDB,
  saveConversationsDB,
  deleteConversationDB,
} from "./conversationsDB";

// ── useConversations ──────────────────────────────────────────────────────────
// Two-tier: IndexedDB cache for immediate display, server for the source of
// truth. Cached conversations are shown immediately on mount so the list is
// never empty on reload while waiting for the server round-trip.

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  const serverFetch = useCallback(async (): Promise<Conversation[]> => {
    const { listConversations } = await import("../api/client");
    const data = await listConversations(50);
    return (data.conversations ?? []) as Conversation[];
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const fresh = await serverFetch();
      if (mountedRef.current) {
        setConversations(fresh);
        // Mirror to IndexedDB so the list survives a reload even when the
        // server is temporarily unreachable.
        saveConversationsDB(fresh).catch(() => {});
      }
    } catch {
      // Server unavailable — keep whatever we already have (which may be
      // the IndexedDB cache loaded on mount).
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [serverFetch]);

  // On mount: load the cached list immediately, then refresh from the server.
  useEffect(() => {
    mountedRef.current = true;
    loadConversationsDB().then((cached) => {
      if (cached && mountedRef.current) {
        setConversations(cached);
        setLoading(false);
      }
    });
    refresh();
    return () => { mountedRef.current = false; };
  }, [refresh]);

  const remove = useCallback(async (id: number) => {
    const { deleteConversation } = await import("../api/client");
    await deleteConversation(id);
    deleteConversationDB(id).catch(() => {});
    setConversations((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const invalidateAndRefresh = useCallback(async () => {
    await refresh();
  }, [refresh]);

  return { conversations, loading, refresh, remove, invalidateAndRefresh };
}
