// ── Canvas History (Undo/Redo) ──────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasState } from "../canvasTypes";
import type { CanvasSetters } from "./types";

function parseSnapshot(json: string): Partial<CanvasState> {
  try {
    return JSON.parse(json);
  } catch {
    return {};
  }
}

export function history(
  { setState }: CanvasSetters,
) {
  const undo = useCallback(() => {
    setState((prev) => {
      if (prev.historyIndex <= 0) return prev;
      const newIndex = prev.historyIndex - 1;
      const snapshot = parseSnapshot(
        prev.history[newIndex],
      );
      const layers = snapshot.layers ?? prev.layers;
      const activeLayerId = layers.some(
        (l) => l.id === prev.activeLayerId,
      )
        ? prev.activeLayerId
        : (layers.at(-1)?.id ?? null);
      const selectedLayerIds =
        activeLayerId !== null
          ? [activeLayerId]
          : ([] as string[]);
      return {
        ...prev,
        ...snapshot,
        activeLayerId,
        selectedLayerIds,
        historyIndex: newIndex,
        _ts: Date.now(),
      };
    });
  }, [setState]);

  const redo = useCallback(() => {
    setState((prev) => {
      if (prev.historyIndex >= prev.history.length - 1)
        return prev;
      const newIndex = prev.historyIndex + 1;
      const snapshot = parseSnapshot(
        prev.history[newIndex],
      );
      const layers = snapshot.layers ?? prev.layers;
      const activeLayerId = layers.some(
        (l) => l.id === prev.activeLayerId,
      )
        ? prev.activeLayerId
        : (layers.at(-1)?.id ?? null);
      const selectedLayerIds =
        activeLayerId !== null
          ? [activeLayerId]
          : ([] as string[]);
      return {
        ...prev,
        ...snapshot,
        activeLayerId,
        selectedLayerIds,
        historyIndex: newIndex,
        _ts: Date.now(),
      };
    });
  }, [setState]);

  return { undo, redo };
}
