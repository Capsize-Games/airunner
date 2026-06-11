// ── Canvas Document Settings ────────────────────────────────────────────
import { useCallback } from "react";
import type { ActiveGridArea, ActiveTool, MoveMode } from "../canvasTypes";
import type { FilterConfig } from "../canvasTypes";
import {
  snapTo8,
  defaultState,
} from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

export function document(
  { setState, recordSnapshot }: CanvasSetters,
) {
  const setActiveTool = useCallback(
    (tool: ActiveTool) => {
      setState((prev) => ({ ...prev, activeTool: tool }));
    },
    [setState],
  );

  const setActiveGridArea = useCallback(
    (area: ActiveGridArea) => {
      setState((prev) => ({
        ...prev,
        activeGridArea: {
          x: Math.max(0, snapTo8(area.x)),
          y: Math.max(0, snapTo8(area.y)),
          width: Math.max(8, snapTo8(area.width)),
          height: Math.max(8, snapTo8(area.height)),
        },
      }));
    },
    [setState],
  );

  const resetDocument = useCallback((fillColor?: string) => {
    try {
      localStorage.removeItem("airunner_canvas_state");
    } catch {
      /* noop */
    }
    // Reset only document *content* — keep all tool settings and view
    // preferences (wand/lasso/bucket options, grid/ruler visibility, brush,
    // active tool, etc.) so creating a new document doesn't wipe them.
    setState((prev) => {
      const fresh = defaultState();
      const layers = fillColor
        ? fresh.layers.map((l) => ({ ...l, fillColor }))
        : fresh.layers;
      return {
        ...prev,
        layers,
        layerGroups: fresh.layerGroups,
        displayOrder: fresh.displayOrder,
        activeLayerId: fresh.activeLayerId,
        selectedLayerIds: fresh.selectedLayerIds,
        selection: null,
        maskStrokes: [],
        documentWidth: fresh.documentWidth,
        documentHeight: fresh.documentHeight,
        documentBgColor: fresh.documentBgColor,
        activeGridArea: fresh.activeGridArea,
        history: fresh.history,
        historyIndex: fresh.historyIndex,
        _ts: Date.now(),
      };
    });
  }, [setState]);

  const moveLayer = useCallback(
    (id: string, x: number, y: number) => {
      setState((prev) =>
        recordSnapshot({
          ...prev,
          layers: prev.layers.map((l) =>
            l.id === id
              ? { ...l, offsetX: x, offsetY: y }
              : l,
          ),
        }),
      );
    },
    [setState, recordSnapshot],
  );

  const setDocumentSize = useCallback(
    (width: number, height: number) => {
      setState((prev) =>
        recordSnapshot({
          ...prev,
          documentWidth: width,
          documentHeight: height,
        }),
      );
    },
    [setState, recordSnapshot],
  );

  const setDocumentBgColor = useCallback(
    (color: string) => {
      setState((prev) =>
        recordSnapshot({
          ...prev,
          documentBgColor: color,
        }),
      );
    },
    [setState, recordSnapshot],
  );

  const setSnapToGrid = useCallback(
    (on: boolean) => {
      setState((prev) => ({
        ...prev,
        snapToGrid: on,
      }));
    },
    [setState],
  );

  const setLayerFilters = useCallback(
    (id: string, filters: FilterConfig[]) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map((l) =>
          l.id === id ? { ...l, filters } : l,
        ),
      }));
    },
    [setState],
  );

  const setMoveMode = useCallback(
    (mode: MoveMode) => {
      setState((prev) => ({ ...prev, moveMode: mode }));
    },
    [setState],
  );

  return {
    setActiveTool,
    setActiveGridArea,
    resetDocument,
    moveLayer,
    setDocumentSize,
    setDocumentBgColor,
    setSnapToGrid,
    setLayerFilters,
    setMoveMode,
  };
}
