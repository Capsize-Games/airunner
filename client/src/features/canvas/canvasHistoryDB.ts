// ── Undo History Persistence (IndexedDB) ──────────────────────────────────
// The undo/redo stack is too large for localStorage (each snapshot embeds the
// full document, including base64 image data). IndexedDB has a much larger
// quota, so the history is mirrored here and restored on reload.
//
// Each saved record carries the document `_ts` it corresponds to. The restore
// is only applied when that `_ts` still matches the freshly-loaded document,
// which guarantees the history is never applied to a different/newer document
// (no stale-history corruption).

const DB_NAME = "airunner_canvas";
const STORE = "history";
const KEY = "default";
const DB_VERSION = 1;

export interface HistoryRecord {
  ts: number;
  history: string[];
  historyIndex: number;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Persist the undo history keyed to the document timestamp it belongs to. */
export async function saveHistoryDB(
  ts: number,
  history: string[],
  historyIndex: number,
): Promise<void> {
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put({ ts, history, historyIndex }, KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    /* IndexedDB unavailable / quota — undo simply won't survive this reload. */
  }
}

/** Load the persisted undo history, or null if none/unavailable. */
export async function loadHistoryDB(): Promise<HistoryRecord | null> {
  try {
    const db = await openDB();
    const rec = await new Promise<HistoryRecord | null>((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(KEY);
      req.onsuccess = () => resolve((req.result as HistoryRecord) ?? null);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return rec;
  } catch {
    return null;
  }
}
