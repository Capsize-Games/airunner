import { useState, useEffect, useCallback } from "react";
import type { EmbeddingInfo } from "../api/embeddings";

// ── useEmbeddings ─────────────────────────────────────────────────────────────
// Server-only: always fetches from the API.

export function useEmbeddings() {
  const [embeddings, setEmbeddings] = useState<EmbeddingInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<EmbeddingInfo[]> => {
    const { listEmbeddings } = await import("../api/client");
    const data = await listEmbeddings();
    return data.embeddings ?? [];
  }, []);

  const sync = useCallback(async () => {
    setLoading(true);
    try {
      const fresh = await serverFetch();
      setEmbeddings(fresh);
    } catch { /* unavailable */ } finally {
      setLoading(false);
    }
  }, [serverFetch]);

  useEffect(() => {
    sync();
  }, [sync]);

  const patchEmbedding = useCallback(async (updated: EmbeddingInfo) => {
    setEmbeddings((prev) => prev.map((e) =>
      e.id === updated.id ? updated : e,
    ));
  }, []);

  return { embeddings, loading, sync, patchEmbedding };
}
