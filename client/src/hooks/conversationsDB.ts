// ── Conversations Cache (IndexedDB) ─────────────────────────────────────────
// The conversation list is too valuable to lose on reload. Mirror it
// in IndexedDB so the chat history panel always has something to show,
// even if the server is temporarily unreachable.
//
// Each conversation record carries an `updated_at` timestamp for
// conflict resolution: newer timestamp wins when merging server data
// with the local cache.

import type { Conversation } from "../types/api";

const DB_NAME = "airunner_conversations";
const STORE = "conversations";
const DB_VERSION = 1;

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Persist the full conversation list to IndexedDB. */
export async function saveConversationsDB(
  conversations: Conversation[],
): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    for (const c of conversations) {
      store.put(c);
    }
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    /* IndexedDB unavailable — conversations won't survive this reload. */
  }
}

/** Load the cached conversation list, or null if none/unavailable. */
export async function loadConversationsDB(): Promise<Conversation[] | null> {
  try {
    const db = await openDB();
    const recs = await new Promise<Conversation[]>((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve((req.result as Conversation[]) ?? []);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return recs.length > 0 ? recs : null;
  } catch {
    return null;
  }
}

/** Delete a single conversation from the cache. */
export async function deleteConversationDB(id: number): Promise<void> {
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    /* IndexedDB unavailable. */
  }
}

/** Clear all cached conversations. */
export async function clearConversationsDB(): Promise<void> {
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    /* IndexedDB unavailable. */
  }
}
