// ── Canvas State Utilities ────────────────────────────────────────────────────
import type { CanvasLayer, CanvasState, LayerGroup,
  StrokeNode } from "./canvasTypes";

// ── ID counter helpers ──────────────────────────────────────────────────────

let _layerIdCounter = 0;
let _strokeIdCounter = 0;
let _imageIdCounter = 0;
let _groupIdCounter = 0;

export const nextLayerId = (): string => `layer_${++_layerIdCounter}`;
export const nextStrokeId = (): string => `stroke_${++_strokeIdCounter}`;
export const nextImageId = (): string => `image_${++_imageIdCounter}`;
export const nextGroupId = (): string => `group_${++_groupIdCounter}`;

/**
 * Advance all module-level ID counters past any IDs found in parsed state,
 * so that new elements don't collide with IDs from loaded/persisted data.
 */
export function advanceCountersFromState(
  state: Partial<CanvasState>,
): void {
  for (const layer of state.layers ?? []) {
    const m = layer.id?.match(/^layer_(\d+)$/);
    if (m) _layerIdCounter = Math.max(_layerIdCounter, Number(m[1]));

    for (const stroke of layer.strokes ?? []) {
      const sm = stroke.id?.match(/^stroke_(\d+)$/);
      if (sm) _strokeIdCounter = Math.max(
        _strokeIdCounter, Number(sm[1]),
      );
    }
    for (const image of layer.images ?? []) {
      const im = image.id?.match(/^image_(\d+)$/);
      if (im) _imageIdCounter = Math.max(
        _imageIdCounter, Number(im[1]),
      );
    }
  }
  for (const group of state.layerGroups ?? []) {
    const gm = group.id?.match(/^group_(\d+)$/);
    if (gm) _groupIdCounter = Math.max(_groupIdCounter, Number(gm[1]));
  }
  for (const stroke of state.maskStrokes ?? []) {
    const sm = stroke.id?.match(/^stroke_(\d+)$/);
    if (sm) _strokeIdCounter = Math.max(
      _strokeIdCounter, Number(sm[1]),
    );
  }
}

// ── Constants & helpers ──────────────────────────────────────────────────────

export const DEFAULT_GRID_SIZE = 512;

export const snapTo8 = (val: number): number =>
  Math.round(val / 8) * 8;

export const pushHistory = (
  snapshots: string[],
  index: number,
  newSnapshot: string,
) => {
  const trimmed = snapshots.slice(0, index + 1);
  const next = [...trimmed, newSnapshot].slice(-50);
  return { history: next, historyIndex: next.length - 1 };
};

export const serialize = (state: CanvasState): string =>
  JSON.stringify({
    _ts: state._ts,
    layers: state.layers,
    activeLayerId: state.activeLayerId,
    selectedLayerIds: state.selectedLayerIds,
    activeGridArea: state.activeGridArea,
    activeTool: state.activeTool,
    brushSize: state.brushSize,
    brushColor: state.brushColor,
    maskStrokes: state.maskStrokes,
    documentWidth: state.documentWidth,
    documentHeight: state.documentHeight,
    documentBgColor: state.documentBgColor,
    snapToGrid: state.snapToGrid,
  });

export const defaultState = (): CanvasState => {
  const firstId = nextLayerId();
  const base = {
    _ts: Date.now(),
    documentWidth: 1024,
    documentHeight: 1024,
    documentBgColor: "transparent",
    layers: [
      {
        id: firstId,
        name: "Background",
        visible: true,
        opacity: 1,
        filters: [] as FilterConfig[],
        images: [] as ImageNode[],
        strokes: [] as StrokeNode[],
        offsetX: 0,
        offsetY: 0,
        parentGroupId: null,
      } as CanvasLayer,
    ],
    layerGroups: [] as LayerGroup[],
    displayOrder: [firstId],
    activeLayerId: firstId,
    selectedLayerIds: [firstId],
    activeGridArea: {
      x: 0, y: 0, width: DEFAULT_GRID_SIZE, height: DEFAULT_GRID_SIZE,
    },
    activeTool: "brush" as ActiveTool,
    brushSize: 10,
    brushColor: "#ffffff",
    maskStrokes: [] as StrokeNode[],
    snapToGrid: false,
  };
  // Seed history with the initial empty state so undo always has a baseline.
  const initialSnapshot = JSON.stringify(base);
  return {
    ...base,
    history: [initialSnapshot],
    historyIndex: 0,
  } as CanvasState;
};

// ── Persistence ──────────────────────────────────────────────────────────────

import type {
  ActiveTool, FilterConfig, ImageNode, ActiveGridArea,
} from "./canvasTypes";

const STORAGE_KEY = "airunner_canvas_state";

/** Load persisted canvas state from localStorage, or null on cache miss. */
export function loadPersistedState(): CanvasState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CanvasState;
    // Validate we have at least the layers array — discard corrupt data.
    if (!Array.isArray(parsed.layers)) return null;
    // Ensure new fields that may be missing from old persisted state.
    parsed.layerGroups ??= [];
    if (
      !Array.isArray(parsed.displayOrder) ||
      parsed.displayOrder.length === 0
    ) {
      const groupIds = parsed.layerGroups.map(
        (g: LayerGroup) => g.id,
      );
      const ungroupedIds = parsed.layers
        .filter((l: CanvasLayer) => !l.parentGroupId)
        .map((l: CanvasLayer) => l.id);
      parsed.displayOrder = [...groupIds, ...ungroupedIds];
    }
    parsed.layers = parsed.layers.map(
      (l) => ({ ...l, parentGroupId: l.parentGroupId ?? null }),
    );
    // Advance counters so new IDs don't collide with loaded ones.
    advanceCountersFromState(parsed);
    return parsed;
  } catch {
    return null;
  }
}

/** Persist canvas state to localStorage. */
export function persistState(state: CanvasState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage may be full — silently discard.
  }
}
