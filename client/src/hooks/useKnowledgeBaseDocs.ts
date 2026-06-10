import { useState, useEffect, useCallback } from "react";
import type { DocumentRecord } from "../types/api";

// ── useKnowledgeBaseDocs ──────────────────────────────────────────────────────
// Server-only: always fetches from the API.

export function useKnowledgeBaseDocs() {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<DocumentRecord[]> => {
    const { listKnowledgeBaseDocuments } = await import("../api/client");
    const data = await listKnowledgeBaseDocuments();
    return data.documents ?? [];
  }, []);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const fresh = await serverFetch();
      setDocs(fresh);
    } catch { /* unavailable */ } finally {
      setLoading(false);
    }
  }, [serverFetch]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    const handler = () => reload();
    window.addEventListener("knowledge-base-changed", handler);
    return () => window.removeEventListener("knowledge-base-changed", handler);
  }, [reload]);

  const toggle = useCallback(async (docId: number) => {
    try {
      const { toggleDocumentActive } = await import("../api/client");
      const result = await toggleDocumentActive(docId);
      setDocs((prev) =>
        prev.map((d) => d.id === docId ? { ...d, active: result.active } : d),
      );
    } catch { /* network error */ }
  }, []);

  return { docs, loading, reload, toggle };
}
