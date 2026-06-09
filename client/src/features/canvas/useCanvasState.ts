// ── Canvas State Hook ────────────────────────────────────────────────────
// Re-export types for backward compatibility.
export type {
  CanvasState,
  CanvasLayer,
  ActiveGridArea,
  ActiveTool,
  MoveMode,
  ImageNode,
  StrokeNode,
  LayerGroup,
  FilterConfig,
} from "./canvasTypes";

import { useMemo } from "react";
import { coreState } from "./state/coreState";
import { layers as layersHook } from "./state/layers";
import { groups as groupsHook } from "./state/groups";
import { selection as selectionHook } from "./state/selection";
import { images as imagesHook } from "./state/images";
import { strokes as strokesHook } from "./state/strokes";
import { masks as masksHook } from "./state/masks";
import { history as historyHook } from "./state/history";
import { brush as brushHook } from "./state/brush";
import { lasso as lassoHook } from "./state/lasso";
import { wand as wandHook } from "./state/wand";
import { bucket as bucketHook } from "./state/bucket";
import { crop as cropHook } from "./state/crop";
import { smudge as smudgeHook } from "./state/smudge";
import { pipette as pipetteHook } from "./state/pipette";
import { zoom as zoomHook } from "./state/zoom";
import { grid as gridHook } from "./state/grid";
import { text as textHook } from "./state/text";
import { document as documentHook } from "./state/document";
import { serialization as serializationHook } from "./state/serialization";

export function useCanvasState() {
  const { state, setters } = coreState();

  // ── Domain hooks ──────────────────────────────────────────────────────
  const layerAPI = layersHook(setters);
  const groupAPI = groupsHook(setters);
  const selectionAPI = selectionHook(setters);
  const imageAPI = imagesHook(setters);
  const strokeAPI = strokesHook(setters);
  const maskAPI = masksHook(setters);
  const historyAPI = historyHook(setters);
  const brushAPI = brushHook(setters);
  const lassoAPI = lassoHook(setters);
  const wandAPI = wandHook(setters);
  const bucketAPI = bucketHook(setters);
  const cropAPI = cropHook(setters);
  const smudgeAPI = smudgeHook(setters);
  const pipetteAPI = pipetteHook(setters);
  const zoomAPI = zoomHook(setters);
  const gridAPI = gridHook(setters);
  const textAPI = textHook(setters);
  const docAPI = documentHook(setters);
  const serializationAPI = serializationHook(state, setters);

  // ── Derived state ─────────────────────────────────────────────────────
  const activeLayer = useMemo(
    () =>
      state.layers.find((l) => l.id === state.activeLayerId) ??
      null,
    [state.layers, state.activeLayerId],
  );

  // ── Composed API (identical shape to the old monolithic return) ───────
  return {
    ...state,
    activeLayer,
    ...layerAPI,
    ...groupAPI,
    ...selectionAPI,
    ...imageAPI,
    ...strokeAPI,
    ...maskAPI,
    ...historyAPI,
    ...brushAPI,
    ...lassoAPI,
    ...wandAPI,
    ...bucketAPI,
    ...cropAPI,
    ...smudgeAPI,
    ...pipetteAPI,
    ...zoomAPI,
    ...gridAPI,
    ...textAPI,
    ...docAPI,
    ...serializationAPI,
  };
}

export type CanvasActions = ReturnType<typeof useCanvasState>;
