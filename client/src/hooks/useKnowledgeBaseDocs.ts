import { useState, useEffect, useCallback } from "react";
import { useDb } from "../db/DbContext";
import { SyncManager } from "../db/SyncManager";
import type { DocumentRecord } from "../types/api";
import type { CachedKbDocument } from "../db/db";

function toCached(d: DocumentRecord): CachedKbDocument {
  return { ...d, cachedAt: Date.now() };
}

// ── useKnowledgeBaseDocs ──────────────────────────────────────────────────────
// Shared hook for KnowledgeBasePanel and ChatView — single source of truth
// for the document list, eliminating the double-fetch on mount.
//
// Toggle strategy: server-wins — optimistic local update, but on toggle we
// immediately re-sync to confirm the new active state.

export function useKnowledgeBaseDocs() {
  const db = useDb();
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const serverFetch = useCallback(async (): Promise<CachedKbDocument[]> => {
    const { listKnowledgeBaseDocuments } = await import("../api/client");
    const data = await listKnowledgeBaseDocuments();
    return (data.documents ?? []).map(toCached);
  }, []);

  const reload = useCallback(async () => {
    if (!db) {
      try {
        const fresh = await serverFetch();
        setDocs(fresh);
      } catch { /* unavailable */ } finally {
        setLoading(false);
      }
      return;
    }

    const manager = new SyncManager(db.kbDocuments, serverFetch, "kbDocuments");

    const cached = await manager.readCached();
    if (cached.length > 0) {
      setDocs(cached);
      setLoading(false);
    }

    try {
      const merged = await manager.sync();
      setDocs(merged);
    } catch { /* stale cache */ } finally {
      setLoading(false);
    }
  }, [db, serverFetch]);

  useEffect(() => {
    reload();
  }, [reload]);

  // Optimistic toggle: flip active in state and cache, then re-fetch to confirm.
  const toggle = useCallback(async (docId: number) => {
    try {
      const { toggleDocumentActive } = await import("../api/client");
      const result = await toggleDocumentActive(docId);
      setDocs((prev) =>
        prev.map((d) => d.id === docId ? { ...d, active: result.active } : d),
      );
      if (db) {
        const existing = await db.kbDocuments.get(docId);
        if (existing) {
          await db.kbDocuments.put({ ...existing, active: result.active, cachedAt: Date.now() });
        }
      }
    } catch {
      // On error, re-sync to restore correct state.
      await reload();
    }
  }, [db, reload]);

  return { docs, loading, reload, toggle };
}
