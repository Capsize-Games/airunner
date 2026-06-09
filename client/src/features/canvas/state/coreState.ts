// ── Canvas Core State ───────────────────────────────────────────────────
// useState init, persistence effects, recordSnapshot factory.

import { useState, useCallback, useEffect, useRef } from "react";
import type { CanvasState } from "../canvasTypes";
import {
  defaultState,
  loadPersistedState,
  loadPersistedStateAsync,
  persistStateSync,
  persistStateAsync,
  serialize,
  pushHistory,
} from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

export function coreState(): {
  state: CanvasState;
  setters: CanvasSetters;
} {
  const [state, setState] = useState<CanvasState>(
    () => loadPersistedState() ?? defaultState(),
  );
  const persistTimer = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const initialLoadDone = useRef(false);

  // On first mount, attempt to load from IndexedDB; it may have a newer
  // state than what localStorage provided synchronously.
  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;
    loadPersistedStateAsync()
      .then((dbState) => {
        if (!dbState) return;
        setState((prev) =>
          dbState._ts > prev._ts ? dbState : prev,
        );
      })
      .catch(() => {});
  }, []);

  // Persist on every state change: localStorage immediately,
  // IndexedDB debounced.
  useEffect(() => {
    persistStateSync(state);
    if (persistTimer.current) clearTimeout(persistTimer.current);
    persistTimer.current = setTimeout(
      () => persistStateAsync(state).catch(() => {}),
      300,
    );
    return () => {
      if (persistTimer.current) clearTimeout(persistTimer.current);
    };
  }, [state]);

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
