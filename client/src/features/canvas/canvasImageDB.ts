// ── Canvas Image Persistence (IndexedDB) ───────────────────────────────────
// Base64 image data embedded in layers is too large for localStorage
// (typical quota 5-10 MB). IndexedDB has a much larger quota, so image
// data is stored here and merged back into the state on reload.
//
// Images are stored keyed by composite key "layerId:imageId" so they can
// be loaded selectively per-layer. Stale images (from deleted layers) are
// cleaned up on each write.

const DB_NAME = "airunner_canvas_images";
const STORE = "images";
const DB_VERSION = 1;

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

/** Save all image src data for the given layers. Cleans up stale keys. */
export async function saveLayerImages(
  layerImages: Array<{ key: string; src: string }>,
): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);

    // Collect the set of keys we are writing.
    const newKeys = new Set(layerImages.map((li) => li.key));

    // Delete stale keys that are not in the current set.
    await new Promise<void>((resolve, reject) => {
      const cursorReq = store.openCursor();
      cursorReq.onsuccess = () => {
        const cursor = cursorReq.result;
        if (cursor) {
          if (!newKeys.has(cursor.key as string)) {
            cursor.delete();
          }
          cursor.continue();
        } else {
          resolve();
        }
      };
      cursorReq.onerror = () => reject(cursorReq.error);
    });

    // Write all current images.
    for (const { key, src } of layerImages) {
      store.put(src, key);
    }

    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    // IndexedDB unavailable — images won't survive this reload.
  }
}

/** Load all image src data, returning a Map of key → src. */
export async function loadLayerImages(): Promise<Map<string, string>> {
  const result = new Map<string, string>();
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const store = tx.objectStore(STORE);
      const cursorReq = store.openCursor();
      cursorReq.onsuccess = () => {
        const cursor = cursorReq.result;
        if (cursor) {
          result.set(cursor.key as string, cursor.value as string);
          cursor.continue();
        } else {
          resolve();
        }
      };
      cursorReq.onerror = () => reject(cursorReq.error);
    });
    db.close();
  } catch {
    // IndexedDB unavailable.
  }
  return result;
}
