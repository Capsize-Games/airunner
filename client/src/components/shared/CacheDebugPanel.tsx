import { useState, useEffect, useCallback } from "react";
import { useDb } from "../../db/DbContext";
import { clearAllCache } from "../../db/evict";

// ── CacheDebugPanel ───────────────────────────────────────────────────────────
// Rendered only when ?debug=cache appears in the URL or in development mode.
// Shows per-table row counts, sync timestamps, and a cache-clear action.

interface TableStat {
  name: string;
  count: number;
  lastSynced: string | null;
}

const SYNC_TABLE_MAP: Record<string, string> = {
  conversations: "conversations",
  messages: "(append-only)",
  loras: "loras",
  embeddings: "embeddings",
  kbDocuments: "kbDocuments",
  civitaiModels: "(TTL-based)",
  civitaiThumbnails: "(cache-miss-only)",
  canvasDocuments: "(timestamp-wins)",
  imageDates: "imageDates",
  images: "(by date)",
};

export default function CacheDebugPanel() {
  const db = useDb();
  const [stats, setStats] = useState<TableStat[]>([]);
  const [clearing, setClearing] = useState(false);

  const refresh = useCallback(async () => {
    if (!db) return;
    const tables = [
      "conversations", "messages", "loras", "embeddings",
      "kbDocuments", "civitaiModels", "civitaiThumbnails",
      "canvasDocuments", "imageDates", "images",
    ] as const;

    const rows = await Promise.all(
      tables.map(async (t) => ({
        name: t,
        count: await (db[t] as import("dexie").Table).count(),
        lastSynced: (() => {
          const syncKey = SYNC_TABLE_MAP[t];
          if (!syncKey || syncKey.startsWith("(")) return null;
          try { return localStorage.getItem(`airunner:sync:${syncKey}`); }
          catch { return null; }
        })(),
      })),
    );
    setStats(rows);
  }, [db]);

  useEffect(() => { refresh(); }, [refresh]);

  const handleClearAll = async () => {
    setClearing(true);
    try {
      await clearAllCache();
      await refresh();
    } finally {
      setClearing(false);
    }
  };

  const handleForceSync = (tableName: string) => {
    const syncKey = SYNC_TABLE_MAP[tableName];
    if (!syncKey || syncKey.startsWith("(")) return;
    try {
      localStorage.removeItem(`airunner:sync:${syncKey}`);
    } catch { /* */ }
    refresh();
  };

  if (!db) {
    return (
      <div style={panelStyle}>
        <strong>Cache Debug</strong>
        <p style={{ color: "#f88", margin: "8px 0 0" }}>
          IndexedDB unavailable (private browsing?)
        </p>
      </div>
    );
  }

  return (
    <div style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <strong>Cache Debug</strong>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="debug-panel-btn" onClick={refresh}>Refresh</button>
          <button className="debug-panel-btn debug-panel-btn-danger" onClick={handleClearAll} disabled={clearing}>
            {clearing ? "Clearing…" : "Clear All"}
          </button>
        </div>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #444" }}>
            <th style={thStyle}>Table</th>
            <th style={{ ...thStyle, textAlign: "right" }}>Rows</th>
            <th style={thStyle}>Last Synced</th>
            <th style={thStyle}></th>
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => (
            <tr key={s.name} style={{ borderBottom: "1px solid #333" }}>
              <td style={tdStyle}>{s.name}</td>
              <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{s.count}</td>
              <td style={{ ...tdStyle, color: s.lastSynced ? "#8f8" : "#888" }}>
                {s.lastSynced
                  ? new Date(s.lastSynced).toLocaleTimeString()
                  : SYNC_TABLE_MAP[s.name]}
              </td>
              <td style={tdStyle}>
                {s.lastSynced && (
                  <button className="debug-panel-btn" onClick={() => handleForceSync(s.name)}>
                    Force Sync
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const panelStyle: React.CSSProperties = {
  position: "fixed",
  bottom: 40,
  right: 56,
  background: "#1a1a2e",
  border: "1px solid #444",
  borderRadius: 6,
  padding: "10px 12px",
  zIndex: 9999,
  minWidth: 380,
  fontFamily: "monospace",
  color: "#ccc",
  fontSize: 12,
  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "3px 6px",
  color: "#888",
  fontWeight: "normal",
};

const tdStyle: React.CSSProperties = {
  padding: "3px 6px",
};
