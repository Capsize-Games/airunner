import { useState, useEffect, useCallback } from "react";
import type { LoraInfo } from "../api/loras";

// ── useLoras ──────────────────────────────────────────────────────────────────
// Server-only: always fetches from the API.

export function useLoras() {
  const [loras, setLoras] = useState<LoraInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<LoraInfo[]> => {
    const { listLoras } = await import("../api/client");
    const data = await listLoras();
    return data.loras ?? [];
  }, []);

  const sync = useCallback(async () => {
    setLoading(true);
    try {
      const fresh = await serverFetch();
      setLoras(fresh);
    } catch { /* unavailable */ } finally {
      setLoading(false);
    }
  }, [serverFetch]);

  useEffect(() => {
    sync();
  }, [sync]);

  const patchLora = useCallback(async (updated: LoraInfo) => {
    setLoras((prev) => prev.map((l) =>
      l.id === updated.id ? { ...l, ...updated } : l,
    ));
  }, []);

  return { loras, loading, sync, patchLora };
}
