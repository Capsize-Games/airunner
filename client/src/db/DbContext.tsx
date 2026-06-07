import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { getDb, type AiRunnerDb } from "./db";

// ── Context ───────────────────────────────────────────────────────────────────
// Provides the Dexie instance (or null when IndexedDB is unavailable, e.g.
// Firefox private mode).  All cache hooks must gracefully fall back to
// direct server fetches when db === null.

const DbContext = createContext<AiRunnerDb | null>(null);

export function DbProvider({ children }: { children: ReactNode }) {
  const [db, setDb] = useState<AiRunnerDb | null>(null);

  useEffect(() => {
    const instance = getDb();
    if (!instance) return;
    // Run a no-op open to confirm IndexedDB is accessible.
    instance.open()
      .then(() => setDb(instance))
      .catch(() => { /* private browsing — leave null */ });
  }, []);

  return <DbContext.Provider value={db}>{children}</DbContext.Provider>;
}

export function useDb(): AiRunnerDb | null {
  return useContext(DbContext);
}
