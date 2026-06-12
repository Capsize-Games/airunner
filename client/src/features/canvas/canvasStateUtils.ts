// ── Canvas State Utilities ────────────────────────────────────────────────────
import type { CanvasLayer, CanvasState, LayerGroup,
  StrokeNode, MoveMode } from "./canvasTypes";

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
    inpaintMaskStrokes: state.inpaintMaskStrokes,
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
    selection: null,
    gridShowGrid: true,
    gridSize: 64,
    gridColor: "#ffffff",
    rulerShowRuler: true,
    activeGridArea: {
      x: 0, y: 0, width: DEFAULT_GRID_SIZE, height: DEFAULT_GRID_SIZE,
    },
    activeTool: "brush" as ActiveTool,
    moveMode: "pick" as MoveMode,
    brushSize: 10,
    brushColor: "#ffffff",
    lassoAntialiasing: true,
    lassoFeatherEdges: false,
    lassoFeatherRadius: 10,
    wandAntialiasing: true,
    wandFeatherEdges: false,
    wandFeatherRadius: 10,
    wandSelectTransparentAreas: true,
    wandSampleMerged: false,
    wandDiagonalNeighbors: false,
    wandThreshold: 15,
    bucketColorSource: "foreground" as const,
    bucketFillTransparentAreas: true,
    bucketAntialiasing: true,
    bucketThreshold: 15,
    smudgeSize: 20,
    pipetteTarget: "foreground" as const,
    textFont: "Arial",
    textSize: 24,
    textColor: "#ffffff",
    maskStrokes: [] as StrokeNode[],
    inpaintMaskStrokes: [] as StrokeNode[],
    snapToGrid: false,
    cropX: 0,
    cropY: 0,
    cropWidth: 512,
    cropHeight: 512,
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
  ActiveTool, FilterConfig, ImageNode,
} from "./canvasTypes";

const CANVAS_DOC_ID = "default";
const LEGACY_STORAGE_KEY = "airunner_canvas_state";

/** Parse and validate a raw CanvasState JSON string. Returns null if invalid. */
function parseCanvasState(raw: string): CanvasState | null {
  try {
    const parsed = JSON.parse(raw) as CanvasState;
    if (!Array.isArray(parsed.layers)) return null;
    parsed.layerGroups ??= [];
    parsed.selection ??= null;
    // The persistable form (used by documentString) strips history. When no
    // usable history survived (e.g. localStorage quota dropped it, or a lean
    // server doc was loaded), seed a baseline snapshot of the loaded document
    // so the very first edit after load is undoable (back to this document).
    if (!Array.isArray(parsed.history) || parsed.history.length === 0) {
      parsed.history = [serialize(parsed)];
      parsed.historyIndex = 0;
    } else if (
      typeof parsed.historyIndex !== "number" ||
      parsed.historyIndex < 0 ||
      parsed.historyIndex >= parsed.history.length
    ) {
      parsed.historyIndex = parsed.history.length - 1;
    }
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
    // Ensure tool settings added after initial release have defaults
    parsed.lassoAntialiasing ??= true;
    parsed.lassoFeatherEdges ??= false;
    parsed.lassoFeatherRadius ??= 10;
    parsed.wandAntialiasing ??= true;
    parsed.wandFeatherEdges ??= false;
    parsed.wandFeatherRadius ??= 10;
    parsed.wandSelectTransparentAreas ??= true;
    parsed.wandSampleMerged ??= false;
    parsed.wandDiagonalNeighbors ??= false;
    parsed.wandThreshold ??= 15;
    parsed.bucketColorSource ??= "foreground";
    parsed.bucketFillTransparentAreas ??= true;
    parsed.bucketAntialiasing ??= true;
    parsed.bucketThreshold ??= 15;
    parsed.smudgeSize ??= 20;
    parsed.pipetteTarget ??= "foreground";
    parsed.textFont ??= "Arial";
    parsed.textSize ??= 24;
    parsed.textColor ??= "#ffffff";
    parsed.cropX ??= 0;
    parsed.cropY ??= 0;
    parsed.cropWidth ??= 512;
    parsed.cropHeight ??= 512;
    parsed.inpaintMaskStrokes ??= [];
    parsed.gridShowGrid ??= true;
    parsed.gridSize ??= 64;
    parsed.gridColor ??= "#ffffff";
    parsed.rulerShowRuler ??= true;
    parsed.zoomDirection ??= "in";
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
 * Persist canvas state to localStorage synchronously.
 */
export async function persistStateAsync(state: CanvasState): Promise<void> {
  try {
    const { history, historyIndex, ...rest } = state;
    void history;
    void historyIndex;
    localStorage.setItem(
      LEGACY_STORAGE_KEY,
      JSON.stringify(rest),
    );
  } catch { /* quota */ }
}

/**
 * Write only to localStorage synchronously. Use this for the immediate
 * write so a fast page reload never loses the latest state.
 */
export function persistStateSync(state: CanvasState): void {
  try {
    // Persist the document WITHOUT history: snapshots embed base64 image data
    // and would exceed the localStorage quota. The undo history is persisted
    // separately in IndexedDB (see canvasHistoryDB) which has a large quota.
    const { history, historyIndex, ...rest } = state;
    void history;
    void historyIndex;
    localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify(rest));
  } catch { /* quota */ }
}

export function persistState(state: CanvasState): void {
  persistStateSync(state);
}
