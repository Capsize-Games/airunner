// ── Canvas Serialization ────────────────────────────────────────────────
import { useCallback } from "react";
import type {
  CanvasState,
  CanvasLayer,
  LayerGroup,
} from "../canvasTypes";
import { advanceCountersFromState, serialize } from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

/** Serialization helpers extracted from the monolithic hook. */

export function serialization(
  state: CanvasState,
  { setState }: CanvasSetters,
) {
  const getSerializedState = useCallback(
    (): CanvasState => state,
    [state],
  );

  const getPersistableState = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { history, historyIndex, ...rest } = state;
    return rest;
  }, [state]);

  const loadFromJSON = useCallback(
    (json: string) => {
      try {
        const data = JSON.parse(json);
        advanceCountersFromState(data);
        setState((prev) => {
          const incomingTs =
            (data as { _ts?: number })._ts ?? 0;
          if (incomingTs > 0 && incomingTs <= prev._ts) {
            return prev;
          }
          let displayOrder = data.displayOrder;
          if (
            !Array.isArray(displayOrder) ||
            displayOrder.length === 0
          ) {
            const groupIds = (
              data.layerGroups ?? []
            ).map((g: LayerGroup) => g.id);
            const ungroupedIds = (data.layers ?? [])
              .filter((l: CanvasLayer) => !l.parentGroupId)
              .map((l: CanvasLayer) => l.id);
            displayOrder = [...groupIds, ...ungroupedIds];
          }
          const next: CanvasState = {
            ...prev,
            _ts: Math.max(prev._ts, incomingTs),
            displayOrder,
            layerGroups:
              data.layerGroups ?? prev.layerGroups,
            layers: (data.layers || prev.layers).map(
              (l: CanvasLayer) => ({
                ...l,
                offsetX: l.offsetX ?? 0,
                offsetY: l.offsetY ?? 0,
                parentGroupId: l.parentGroupId ?? null,
              }),
            ),
            activeLayerId:
              data.activeLayerId ?? prev.activeLayerId,
            selectedLayerIds:
              data.selectedLayerIds ?? prev.selectedLayerIds,
            activeGridArea:
              data.activeGridArea || prev.activeGridArea,
            activeTool:
              data.activeTool || ("brush" as const),
            moveMode:
              data.moveMode ?? prev.moveMode,
            brushSize:
              data.brushSize ?? prev.brushSize,
            brushColor:
              data.brushColor || prev.brushColor,
            maskStrokes: data.maskStrokes || [],
            documentWidth:
              data.documentWidth ?? prev.documentWidth,
            documentHeight:
              data.documentHeight ?? prev.documentHeight,
            documentBgColor:
              data.documentBgColor ?? prev.documentBgColor,
            snapToGrid:
              data.snapToGrid ?? prev.snapToGrid,
            selection: data.selection ?? prev.selection ?? null,
          };

          // A strictly newer document replaced the content (e.g. edited in
          // another tab/client) → start a fresh baseline. For an equal/unknown
          // timestamp keep the existing history (which may have just been
          // restored from localStorage on reload), seeding a baseline only if
          // none exists. This preserves undo/redo across reloads.
          if (incomingTs > prev._ts) {
            return { ...next, history: [serialize(next)], historyIndex: 0 };
          }
          if (!Array.isArray(next.history) || next.history.length === 0) {
            return { ...next, history: [serialize(next)], historyIndex: 0 };
          }
          return next;
        });
      } catch {
        /* ignore */
      }
    },
    [setState],
  );

  return { getSerializedState, getPersistableState, loadFromJSON };
}
