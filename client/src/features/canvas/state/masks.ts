// ── Canvas Mask Operations ──────────────────────────────────────────────
import { useCallback } from "react";
import type { StrokeNode } from "../canvasTypes";
import { nextStrokeId } from "../canvasStateUtils";
import {
  serialize,
  pushHistory,
} from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

export function masks(
  { setState, recordSnapshot }: CanvasSetters,
) {
  const addLayerMask = useCallback(
    (layerId: string, fill: "white" | "black" = "white") => {
      setState((prev) => {
        const snap = recordSnapshot(prev);
        return {
          ...snap,
          layers: snap.layers.map((l) =>
            l.id === layerId
              ? {
                  ...l,
                  maskStrokes: [],
                  maskFill: fill,
                  maskTarget: "mask" as const,
                }
              : l,
          ),
        };
      });
    },
    [setState, recordSnapshot],
  );

  const removeLayerMask = useCallback(
    (layerId: string) => {
      setState((prev) => {
        const snap = recordSnapshot(prev);
        return {
          ...snap,
          layers: snap.layers.map((l) =>
            l.id === layerId
              ? { ...l, maskStrokes: null }
              : l,
          ),
        };
      });
    },
    [setState, recordSnapshot],
  );

  const addLayerMaskStroke = useCallback(
    (layerId: string, stroke: Omit<StrokeNode, "id">) => {
      setState((prev) => {
        const newStroke: StrokeNode = {
          ...stroke,
          id: nextStrokeId(),
        };
        const layers = prev.layers.map((l) =>
          l.id === layerId
            ? {
                ...l,
                maskStrokes: [
                  ...(l.maskStrokes ?? []),
                  newStroke,
                ],
              }
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

  const setLayerMaskTarget = useCallback(
    (
      layerId: string,
      target: "content" | "mask",
    ) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map((l) =>
          l.id === layerId
            ? { ...l, maskTarget: target }
            : l,
        ),
      }));
    },
    [setState],
  );

  return {
    addLayerMask,
    removeLayerMask,
    addLayerMaskStroke,
    setLayerMaskTarget,
  };
}
