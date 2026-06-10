import { useState, useEffect, useCallback } from "react";
import type { Conversation } from "../types/api";

// ── useConversations ──────────────────────────────────────────────────────────
// Server-only: always fetches from the API.

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<Conversation[]> => {
    const { listConversations } = await import("../api/client");
    const data = await listConversations(50);
    return (data.conversations ?? []) as Conversation[];
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const fresh = await serverFetch();
      setConversations(fresh);
    } catch {
      /* daemon unavailable */
    } finally {
      setLoading(false);
    }
  }, [serverFetch]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const remove = useCallback(async (id: number) => {
    const { deleteConversation } = await import("../api/client");
    await deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const invalidateAndRefresh = useCallback(async () => {
    await refresh();
  }, [refresh]);

  return { conversations, loading, refresh, remove, invalidateAndRefresh };
}
