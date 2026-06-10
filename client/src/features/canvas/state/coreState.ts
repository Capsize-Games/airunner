// ── Canvas Core State ───────────────────────────────────────────────────
// useState init, persistence effects, recordSnapshot factory.

import { useState, useCallback, useEffect } from "react";
import type { CanvasState } from "../canvasTypes";
import {
  defaultState,
  loadPersistedState,
  persistStateSync,
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

  // Persist on every state change to localStorage immediately.
  useEffect(() => {
    persistStateSync(state);
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
