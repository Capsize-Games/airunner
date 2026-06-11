// ── Tool Preset Reset ───────────────────────────────────────────────────
// Restores a tool's settings (or every tool's) to their factory defaults.
import { useCallback } from "react";
import type { CanvasState, ActiveTool } from "../canvasTypes";
import { defaultState } from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

type StateKey = keyof CanvasState;

// Which CanvasState fields constitute each tool's user-configurable preset.
const TOOL_SETTING_KEYS: Partial<Record<ActiveTool, StateKey[]>> = {
  brush: ["brushSize", "brushColor"],
  eraser: ["brushSize"],
  mask: ["brushSize"],
  lasso: ["lassoAntialiasing", "lassoFeatherEdges", "lassoFeatherRadius"],
  wand: [
    "wandAntialiasing", "wandFeatherEdges", "wandFeatherRadius",
    "wandSelectTransparentAreas", "wandSampleMerged",
    "wandDiagonalNeighbors", "wandThreshold",
  ],
  bucket: [
    "bucketColorSource", "bucketFillTransparentAreas",
    "bucketAntialiasing", "bucketThreshold",
  ],
  smudge: ["smudgeSize"],
  pipette: ["pipetteTarget"],
  text: ["textFont", "textSize", "textColor"],
  crop: ["cropX", "cropY", "cropWidth", "cropHeight"],
  grid: ["gridShowGrid", "gridSize", "gridColor", "snapToGrid"],
  ruler: ["rulerShowRuler"],
  zoom: ["zoomDirection"],
  move: ["moveMode"],
};

/** Build a partial state restoring `keys` to their defaults. */
function defaultsFor(keys: StateKey[], fresh: CanvasState): Partial<CanvasState> {
  const patch: Record<string, unknown> = {};
  for (const k of keys) patch[k] = fresh[k];
  return patch as Partial<CanvasState>;
}

export function presets({ setState }: CanvasSetters) {
  /** Reset a single tool's settings to defaults. */
  const resetToolPresets = useCallback(
    (tool: ActiveTool) => {
      const keys = TOOL_SETTING_KEYS[tool];
      if (!keys || keys.length === 0) return;
      setState((prev) => ({ ...prev, ...defaultsFor(keys, defaultState()) }));
    },
    [setState],
  );

  /** Reset every tool's settings to defaults. */
  const resetAllToolPresets = useCallback(() => {
    setState((prev) => {
      const fresh = defaultState();
      const allKeys = Object.values(TOOL_SETTING_KEYS).flat();
      return { ...prev, ...defaultsFor(allKeys, fresh) };
    });
  }, [setState]);

  return { resetToolPresets, resetAllToolPresets };
}
