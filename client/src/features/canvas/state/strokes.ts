// ── Canvas Stroke Operations ────────────────────────────────────────────
import { useCallback } from "react";
import type { StrokeNode } from "../canvasTypes";
import { nextStrokeId } from "../canvasStateUtils";
import {
  serialize,
  pushHistory,
} from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

export function strokes(
  { setState }: CanvasSetters,
) {
  const addStroke = useCallback(
    (stroke: Omit<StrokeNode, "id">) => {
      setState((prev) => {
        const activeIdx = prev.layers.findIndex(
          (l) => l.id === prev.activeLayerId,
        );
        if (activeIdx === -1) return prev;
        const newStroke: StrokeNode = {
          ...stroke,
          id: nextStrokeId(),
        };
        const layers = prev.layers.map((l, i) =>
          i === activeIdx
            ? { ...l, strokes: [...l.strokes, newStroke] }
            : l,
        );
        const next = { ...prev, _ts: Date.now(), layers };
        const { history, historyIndex } = pushHistory(
          prev.history,
          prev.historyIndex,
          serialize(next),
        );
        return { ...next, history, historyIndex };
      });
    },
    [setState],
  );

  const addMaskStroke = useCallback(
    (stroke: Omit<StrokeNode, "id">) => {
      setState((prev) => {
        const newStroke: StrokeNode = {
          ...stroke,
          id: nextStrokeId(),
        };
        const next = {
          ...prev,
          _ts: Date.now(),
          maskStrokes: [...prev.maskStrokes, newStroke],
        };
        const { history, historyIndex } = pushHistory(
          prev.history,
          prev.historyIndex,
          serialize(next),
        );
        return { ...next, history, historyIndex };
      });
    },
    [setState],
  );

  const clearMask = useCallback(() => {
    setState((prev) => {
      const next = { ...prev, maskStrokes: [] };
      const { history, historyIndex } = pushHistory(
        prev.history,
        prev.historyIndex,
        serialize(next),
      );
      return { ...next, history, historyIndex };
    });
  }, [setState]);

  return { addStroke, addMaskStroke, clearMask };
}
