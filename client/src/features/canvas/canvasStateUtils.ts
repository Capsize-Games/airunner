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
    layerGroups: state.layerGroups,
    displayOrder: state.displayOrder,
    activeGridArea: state.activeGridArea,
    maskStrokes: state.maskStrokes,
    documentWidth: state.documentWidth,
    documentHeight: state.documentHeight,
    documentBgColor: state.documentBgColor,
    // NOTE: activeTool, brushSize, brushColor, snapToGrid, activeLayerId,
    // and selectedLayerIds are deliberately excluded from history snapshots
    // so undo/redo only restores document content – never the user's
    // current tool, brush settings, layer selection, or grid preference.
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
import { getDb } from "../../db/db";

const CANVAS_DOC_ID = "default";
const LEGACY_STORAGE_KEY = "airunner_canvas_state";

/** Parse and validate a raw CanvasState JSON string. Returns null if invalid. */
function parseCanvasState(raw: string): CanvasState | null {
  try {
    const parsed = JSON.parse(raw) as CanvasState;
    if (!Array.isArray(parsed.layers)) return null;
    parsed.layerGroups ??= [];
    // The persistable form (used by documentString) strips history;
    // ensure defaults are present so pushHistory / undo don't crash.
    parsed.history ??= [];
    parsed.historyIndex ??= -1;
    if (
      !Array.isArray(parsed.displayOrder) ||
      parsed.displayOrder.length === 0
    ) {
      const groupIds = parsed.layerGroups.map((g: LayerGroup) => g.id);
      const ungroupedIds = parsed.layers
        .filter((l: CanvasLayer) => !l.parentGroupId)
        .map((l: CanvasLayer) => l.id);
      parsed.displayOrder = [...groupIds, ...ungroupedIds];
    }
    parsed.layers = parsed.layers.map(
      (l) => ({ ...l, parentGroupId: l.parentGroupId ?? null }),
    );
    advanceCountersFromState(parsed);
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Load canvas state synchronously from localStorage (legacy fallback used on
 * first render before IndexedDB is ready).
 */
export function loadPersistedState(): CanvasState | null {
  try {
    const raw = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return null;
    return parseCanvasState(raw);
  } catch {
    return null;
  }
}

/**
 * Load canvas state from IndexedDB asynchronously.
 * Returns null on cache miss or when IndexedDB is unavailable.
 */
export async function loadPersistedStateAsync(): Promise<CanvasState | null> {
  const db = getDb();
  if (!db) return null;
  try {
    const record = await db.canvasDocuments.get(CANVAS_DOC_ID);
    if (!record) return null;
    return parseCanvasState(record.documentJson);
  } catch {
    return null;
  }
}

/**
 * Persist canvas state to IndexedDB (primary) and keep localStorage in sync
 * as a fallback for the synchronous first-render load.
 */
export async function persistStateAsync(state: CanvasState): Promise<void> {
  const json = JSON.stringify(state);

  // Keep localStorage in sync for synchronous first-render load.
  try {
    localStorage.setItem(LEGACY_STORAGE_KEY, json);
  } catch { /* quota */ }

  const db = getDb();
  if (!db) return;
  try {
    await db.canvasDocuments.put({
      id: CANVAS_DOC_ID,
      documentJson: json,
      updatedAt: state._ts,
    });
  } catch { /* quota or unavailable */ }
}

/**
 * Write only to localStorage synchronously. Use this for the immediate
 * write so a fast page reload never loses the latest state.
 */
export function persistStateSync(state: CanvasState): void {
  try {
    localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(state));
  } catch { /* quota */ }
}

/** Kept for callers that still use the synchronous form (canvas WebSocket). */
export function persistState(state: CanvasState): void {
  persistStateSync(state);
  // Fire-and-forget async write.
  persistStateAsync(state).catch(() => {});
}
