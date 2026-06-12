// ── Canvas Core State ───────────────────────────────────────────────────
// useState init, persistence effects, recordSnapshot factory.

import { useState, useCallback, useEffect, useRef } from "react";
import type { CanvasState } from "../canvasTypes";
import {
  defaultState,
  loadPersistedState,
  persistStateSync,
  persistImagesToDB,
  mergeStoredImages,
  serialize,
  pushHistory,
} from "../canvasStateUtils";
import { saveHistoryDB, loadHistoryDB } from "../canvasHistoryDB";
import type { CanvasSetters } from "./types";

export function coreState(): {
  state: CanvasState;
  setters: CanvasSetters;
} {
  const [state, setState] = useState<CanvasState>(
    () => loadPersistedState() ?? defaultState(),
  );

  // Flag to suppress persistStateSync + persistImagesToDB during image
  // restoration so we don't trigger an infinite loop.
  const restoringImagesRef = useRef(false);

  // Persist the document to localStorage immediately (images already
  // stripped), and mirror images to IndexedDB asynchronously.
  const histTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    persistStateSync(state);
    if (!restoringImagesRef.current) {
      void persistImagesToDB(state);
    }
    if (histTimer.current) clearTimeout(histTimer.current);
    const ts = state._ts;
    const history = state.history;
    const historyIndex = state.historyIndex;
    histTimer.current = setTimeout(() => {
      void saveHistoryDB(ts, history, historyIndex);
    }, 300);
  }, [state]);

  // One-time restore of layer images from IndexedDB on mount. Must run
  // before the history restore so the document state is complete when
  // undo snapshots are seeded.
  const imagesRestoredRef = useRef(false);
  useEffect(() => {
    let cancelled = false;
    void mergeStoredImages(state).then((merged) => {
      if (cancelled || imagesRestoredRef.current) return;
      imagesRestoredRef.current = true;
      if (merged === state) return; // no images to restore
      restoringImagesRef.current = true;
      setState(merged);
      // Reset the flag on the next tick so subsequent edits persist normally.
      setTimeout(() => {
        restoringImagesRef.current = false;
      }, 0);
    });
    return () => {
      cancelled = true;
    };
    // Only run on mount — `state` in the closure is the initial state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // One-time restore of the undo history from IndexedDB on mount. Only applied
  // when its timestamp still matches the loaded document (so it's never applied
  // to a different/newer doc) and the user hasn't started editing yet.
  const historyRestoredRef = useRef(false);
  useEffect(() => {
    let cancelled = false;
    void loadHistoryDB().then((rec) => {
      if (cancelled || historyRestoredRef.current || !rec) return;
      historyRestoredRef.current = true;
      setState((prev) => {
        if (prev._ts !== rec.ts) return prev; // doc moved on → history is stale
        if (prev.historyIndex !== 0 || prev.history.length > 1) return prev; // already edited
        if (
          !Array.isArray(rec.history) || rec.history.length <= 1 ||
          typeof rec.historyIndex !== "number" ||
          rec.historyIndex < 0 || rec.historyIndex >= rec.history.length
        ) {
          return prev;
        }
        return { ...prev, history: rec.history, historyIndex: rec.historyIndex };
      });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const recordSnapshot = useCallback(
    (prev: CanvasState): CanvasState => {
      const snapshot = serialize(prev);
      const { history, historyIndex } = pushHistory(
        prev.history,
        prev.historyIndex,
        snapshot,
      );
      return {
        ...prev,
        _ts: Date.now(),
        history,
        historyIndex,
      };
    },
    [],
  );

  const setters: CanvasSetters = { setState, recordSnapshot };
  return { state, setters };
}
