// ── Canvas Core State ───────────────────────────────────────────────────
// useState init, persistence effects, recordSnapshot factory.

import { useState, useCallback, useEffect, useRef } from "react";
import type { CanvasState } from "../canvasTypes";
import {
  defaultState,
  loadPersistedState,
  persistStateSync,
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

  // Persist the document to localStorage immediately, and mirror the (larger)
  // undo history to IndexedDB on a short debounce.
  const histTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    persistStateSync(state);
    if (histTimer.current) clearTimeout(histTimer.current);
    const ts = state._ts;
    const history = state.history;
    const historyIndex = state.historyIndex;
    histTimer.current = setTimeout(() => {
      void saveHistoryDB(ts, history, historyIndex);
    }, 300);
  }, [state]);

  // One-time restore of the undo history from IndexedDB on mount. Only applied
  // when its timestamp still matches the loaded document (so it's never applied
  // to a different/newer doc) and the user hasn't started editing yet.
  const restoredRef = useRef(false);
  useEffect(() => {
    let cancelled = false;
    void loadHistoryDB().then((rec) => {
      if (cancelled || restoredRef.current || !rec) return;
      restoredRef.current = true;
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
