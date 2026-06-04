import { useState, useCallback, useMemo, useEffect, useRef } from "react";

// ── Types ───────────────────────────────────────────────────────────────────

export interface FilterConfig {
  type: "blur" | "pixelate" | "noise" | "brighten" | "contrast" | "grayscale";
  params: Record<string, number>;
}

export interface ImageNode {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  src: string; // base64 data URL
}

export interface StrokeNode {
  id: string;
  points: number[];
  color: string;
  strokeWidth: number;
  tool: "brush" | "eraser";
}

export interface CanvasLayer {
  id: string;
  name: string;
  visible: boolean;
  opacity: number; // 0–1
  filters: FilterConfig[];
  images: ImageNode[];
  strokes: StrokeNode[];
  offsetX: number;
  offsetY: number;
  parentGroupId: string | null;
}

export interface LayerGroup {
  id: string;
  name: string;
  expanded: boolean;
}

export interface ActiveGridArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type ActiveTool = "select" | "brush" | "eraser" | "mask" | "move";

export interface CanvasState {
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string; // hex or 'transparent'
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  activeLayerId: string | null;
  selectedLayerIds: string[];
  activeGridArea: ActiveGridArea;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  snapToGrid: boolean;
  history: string[];
  historyIndex: number;
}

// ── ID counter helpers ──────────────────────────────────────────────────────

let _layerIdCounter = 0;
let _strokeIdCounter = 0;
let _imageIdCounter = 0;
let _groupIdCounter = 0;

const nextLayerId = (): string => `layer_${++_layerIdCounter}`;
const nextStrokeId = (): string => `stroke_${++_strokeIdCounter}`;
const nextImageId = (): string => `image_${++_imageIdCounter}`;
const nextGroupId = (): string => `group_${++_groupIdCounter}`;

/**
 * Advance all module-level ID counters past any IDs found in parsed state,
 * so that new elements don't collide with IDs from loaded/persisted data.
 */
function advanceCountersFromState(state: Partial<CanvasState>): void {
  for (const layer of state.layers ?? []) {
    const m = layer.id?.match(/^layer_(\d+)$/);
    if (m) _layerIdCounter = Math.max(_layerIdCounter, Number(m[1]));

    for (const stroke of layer.strokes ?? []) {
      const sm = stroke.id?.match(/^stroke_(\d+)$/);
      if (sm) _strokeIdCounter = Math.max(_strokeIdCounter, Number(sm[1]));
    }
    for (const image of layer.images ?? []) {
      const im = image.id?.match(/^image_(\d+)$/);
      if (im) _imageIdCounter = Math.max(_imageIdCounter, Number(im[1]));
    }
  }
  for (const group of state.layerGroups ?? []) {
    const gm = group.id?.match(/^group_(\d+)$/);
    if (gm) _groupIdCounter = Math.max(_groupIdCounter, Number(gm[1]));
  }
  for (const stroke of state.maskStrokes ?? []) {
    const sm = stroke.id?.match(/^stroke_(\d+)$/);
    if (sm) _strokeIdCounter = Math.max(_strokeIdCounter, Number(sm[1]));
  }
}

const DEFAULT_GRID_SIZE = 512;

const snapTo8 = (val: number): number => Math.round(val / 8) * 8;

const pushHistory = (snapshots: string[], index: number, newSnapshot: string) => {
  const trimmed = snapshots.slice(0, index + 1);
  const next = [...trimmed, newSnapshot].slice(-50);
  return { history: next, historyIndex: next.length - 1 };
};

const serialize = (state: CanvasState): string =>
  JSON.stringify({
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

const defaultState = (): CanvasState => {
  const firstId = nextLayerId();
  const base = {
    documentWidth: 1024,
    documentHeight: 1024,
    documentBgColor: "transparent",
    layers: [
      {
        id: firstId,
        name: "Background",
        visible: true,
        opacity: 1,
        filters: [],
        images: [],
        strokes: [],
        offsetX: 0,
        offsetY: 0,
        parentGroupId: null,
      },
    ],
    layerGroups: [],
    activeLayerId: firstId,
    selectedLayerIds: [firstId],
    activeGridArea: { x: 0, y: 0, width: DEFAULT_GRID_SIZE, height: DEFAULT_GRID_SIZE },
    activeTool: "brush" as ActiveTool,
    brushSize: 10,
    brushColor: "#ffffff",
    maskStrokes: [],
    snapToGrid: false,
  };
  // Seed history with the initial empty state so undo always has a baseline.
  const initialSnapshot = JSON.stringify(base);
  return { ...base, history: [initialSnapshot], historyIndex: 0 };
};

// ── Helpers ──────────────────────────────────────────────────────────────────

const STORAGE_KEY = "airunner_canvas_state";

/** Load persisted canvas state from localStorage, or null on cache miss. */
function loadPersistedState(): CanvasState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CanvasState;
    // Validate we have at least layers — discard corrupt data.
    if (!Array.isArray(parsed.layers) || parsed.layers.length === 0) return null;
    // Ensure new fields that may be missing from old persisted state.
    parsed.layerGroups ??= [];
    parsed.layers = parsed.layers.map((l) => ({ ...l, parentGroupId: l.parentGroupId ?? null }));
    // Advance counters so new IDs don't collide with loaded ones.
    advanceCountersFromState(parsed);
    return parsed;
  } catch {
    return null;
  }
}

/** Persist canvas state to localStorage (synchronous, no debounce needed). */
function persistState(state: CanvasState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage may be full — silently discard.
  }
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useCanvasState() {
  const [state, setState] = useState<CanvasState>(
    () => loadPersistedState() ?? defaultState(),
  );
  const persistTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced localStorage persistence — writes 300 ms after last change.
  useEffect(() => {
    if (persistTimer.current) clearTimeout(persistTimer.current);
    persistTimer.current = setTimeout(() => persistState(state), 300);
    return () => {
      if (persistTimer.current) clearTimeout(persistTimer.current);
    };
  }, [state]);

  const recordSnapshot = useCallback((prev: CanvasState): CanvasState => {
    const snapshot = serialize(prev);
    const { history, historyIndex } = pushHistory(prev.history, prev.historyIndex, snapshot);
    return { ...prev, history, historyIndex };
  }, []);

  // ── Layer operations ──────────────────────────────────────────────────────

  const addLayer = useCallback(() => {
    setState((prev) => {
      const newLayer: CanvasLayer = {
        id: nextLayerId(),
        name: `Layer ${prev.layers.length + 1}`,
        visible: true,
        opacity: 1,
        filters: [],
        images: [],
        strokes: [],
        offsetX: 0,
        offsetY: 0,
        parentGroupId: null,
      };
      return recordSnapshot({ ...prev, layers: [...prev.layers, newLayer], activeLayerId: newLayer.id });
    });
  }, [recordSnapshot]);

  const deleteLayer = useCallback((id: string) => {
    setState((prev) => {
      if (prev.layers.length <= 1) return prev;
      const filtered = prev.layers.filter((l) => l.id !== id);
      let newActive = prev.activeLayerId;
      if (newActive === id) newActive = filtered.at(-1)?.id ?? null;
      const cleanedSelection = prev.selectedLayerIds.filter(
        (s) => s !== id,
      );
      return recordSnapshot({
        ...prev,
        layers: filtered,
        activeLayerId: newActive,
        selectedLayerIds:
          cleanedSelection.length > 0
            ? cleanedSelection
            : newActive
              ? [newActive]
              : [],
      });
    });
  }, [recordSnapshot]);

  const renameLayer = useCallback((id: string, name: string) => {
    setState((prev) => ({
      ...prev,
      layers: prev.layers.map((l) => (l.id === id ? { ...l, name } : l)),
    }));
  }, []);

  const setLayerVisible = useCallback((id: string, visible: boolean) => {
    setState((prev) => ({
      ...prev,
      layers: prev.layers.map((l) => (l.id === id ? { ...l, visible } : l)),
    }));
  }, []);

  const setLayerOpacity = useCallback((id: string, opacity: number) => {
    setState((prev) => ({
      ...prev,
      layers: prev.layers.map((l) => (l.id === id ? { ...l, opacity } : l)),
    }));
  }, []);

  const reorderLayer = useCallback((id: string, direction: "up" | "down") => {
    setState((prev) => {
      const idx = prev.layers.findIndex((l) => l.id === id);
      if (idx === -1) return prev;
      const layers = [...prev.layers];
      if (direction === "up" && idx < layers.length - 1) {
        [layers[idx], layers[idx + 1]] = [layers[idx + 1], layers[idx]];
      } else if (direction === "down" && idx > 0) {
        [layers[idx], layers[idx - 1]] = [layers[idx - 1], layers[idx]];
      } else return prev;
      return recordSnapshot({ ...prev, layers });
    });
  }, [recordSnapshot]);

  const setActiveLayer = useCallback((id: string) => {
    setState((prev) => ({ ...prev, activeLayerId: id, selectedLayerIds: [id] }));
  }, []);

  // ── Layer group operations ────────────────────────────────────────────────

  const addLayerGroup = useCallback(() => {
    setState((prev) => ({
      ...prev,
      layerGroups: [
        ...prev.layerGroups,
        { id: nextGroupId(), name: `Group ${prev.layerGroups.length + 1}`, expanded: true },
      ],
    }));
  }, []);

  const toggleGroupExpanded = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      layerGroups: prev.layerGroups.map((g) =>
        g.id === id ? { ...g, expanded: !g.expanded } : g,
      ),
    }));
  }, []);

  const renameGroup = useCallback((id: string, name: string) => {
    setState((prev) => ({
      ...prev,
      layerGroups: prev.layerGroups.map((g) =>
        g.id === id ? { ...g, name } : g,
      ),
    }));
  }, []);

  const deleteGroup = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      layerGroups: prev.layerGroups.filter((g) => g.id !== id),
      layers: prev.layers.map((l) =>
        l.parentGroupId === id ? { ...l, parentGroupId: null } : l,
      ),
    }));
  }, []);

  const moveLayerToGroup = useCallback((layerId: string, groupId: string | null) => {
    setState((prev) => ({
      ...prev,
      layers: prev.layers.map((l) =>
        l.id === layerId ? { ...l, parentGroupId: groupId } : l,
      ),
    }));
  }, []);

  /** Ctrl/cmd+click: toggle a layer in/out of the multi-selection. */
  const toggleLayerSelection = useCallback((id: string) => {
    setState((prev) => {
      const isSelected = prev.selectedLayerIds.includes(id);
      const nextSelection = isSelected
        ? prev.selectedLayerIds.filter((s) => s !== id)
        : [...prev.selectedLayerIds, id];
      // Ensure at least one layer remains selected.
      if (nextSelection.length === 0) return prev;
      return {
        ...prev,
        selectedLayerIds: nextSelection,
      };
    });
  }, []);

  /** Shift+click: select a contiguous range from the active layer. */
  const selectLayerRange = useCallback((id: string) => {
    setState((prev) => {
      const startIdx = prev.layers.findIndex(
        (l) => l.id === prev.activeLayerId,
      );
      const endIdx = prev.layers.findIndex((l) => l.id === id);
      if (startIdx === -1 || endIdx === -1) return prev;
      const lo = Math.min(startIdx, endIdx);
      const hi = Math.max(startIdx, endIdx);
      const rangeIds = prev.layers.slice(lo, hi + 1).map((l) => l.id);
      return { ...prev, selectedLayerIds: rangeIds, activeLayerId: id };
    });
  }, []);

  /** Drag-and-drop reorder: move a layer to a specific index (0 = bottom). */
  const reorderLayerToIndex = useCallback((id: string, toIndex: number) => {
    setState((prev) => {
      const fromIdx = prev.layers.findIndex((l) => l.id === id);
      if (fromIdx === -1 || fromIdx === toIndex) return prev;
      const layers = [...prev.layers];
      const [moved] = layers.splice(fromIdx, 1);
      // Adjust toIndex after removal if needed.
      const adjusted = toIndex > fromIdx ? toIndex - 1 : toIndex;
      layers.splice(adjusted, 0, moved);
      return recordSnapshot({ ...prev, layers });
    });
  }, [recordSnapshot]);

  /** Merge selected layers downward into the layer below the selection. */
  const mergeSelectedLayers = useCallback(() => {
    setState((prev) => {
      const sel = prev.selectedLayerIds;
      if (sel.length < 1) return prev;

      // Sort selected by index ascending (0 = bottom of stack).
      const sorted = [...sel]
        .map((id) => ({ id, idx: prev.layers.findIndex((l) => l.id === id) }))
        .filter((e) => e.idx !== -1)
        .sort((a, b) => a.idx - b.idx);

      if (sorted.length === 0) return prev;

      // The layer directly below the bottommost selected layer.
      const targetIdx = sorted[0].idx - 1;
      if (targetIdx < 0) return prev; // nothing to merge into

      const targetId = prev.layers[targetIdx].id;
      const mergeIds = new Set(sorted.map((e) => e.id));

      // Collect all content from selected layers.
      const extraImages: ImageNode[] = [];
      const extraStrokes: StrokeNode[] = [];
      for (const { id } of sorted) {
        const mLayer = prev.layers.find((l) => l.id === id);
        if (!mLayer) continue;
        extraImages.push(...mLayer.images);
        extraStrokes.push(...mLayer.strokes);
      }

      const mergedLayers = prev.layers
        .filter((l) => !mergeIds.has(l.id))
        .map((l) =>
          l.id === targetId
            ? { ...l, images: [...l.images, ...extraImages], strokes: [...l.strokes, ...extraStrokes] }
            : l,
        );

      return recordSnapshot({
        ...prev,
        layers: mergedLayers,
        selectedLayerIds: [targetId],
        activeLayerId: targetId,
      });
    });
  }, [recordSnapshot]);

  // ── Active tool ───────────────────────────────────────────────────────────

  const setActiveTool = useCallback((tool: ActiveTool) => {
    setState((prev) => ({ ...prev, activeTool: tool }));
  }, []);

  // ── Active grid area ──────────────────────────────────────────────────────

  const setActiveGridArea = useCallback((area: ActiveGridArea) => {
    setState((prev) => ({
      ...prev,
      activeGridArea: {
        x: Math.max(0, snapTo8(area.x)),
        y: Math.max(0, snapTo8(area.y)),
        width: Math.max(8, snapTo8(area.width)),
        height: Math.max(8, snapTo8(area.height)),
      },
    }));
  }, []);

  // ── Reset document ────────────────────────────────────────────────────────

  const resetDocument = useCallback(() => {
    // Wipe localStorage immediately so a reload after reset sees a clean slate
    // even if the debounced persist hasn't fired yet.
    // Do NOT reset module-level ID counters — that would cause duplicate IDs
    // with persisted data from the current session.
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    setState(defaultState());
  }, []);

  // ── Move layer ────────────────────────────────────────────────────────────

  const moveLayer = useCallback((id: string, x: number, y: number) => {
    setState((prev) => recordSnapshot({
      ...prev,
      layers: prev.layers.map((l) => l.id === id ? { ...l, offsetX: x, offsetY: y } : l),
    }));
  }, [recordSnapshot]);

  // ── Document settings ─────────────────────────────────────────────────────

  const setDocumentSize = useCallback((width: number, height: number) => {
    setState((prev) => recordSnapshot({ ...prev, documentWidth: width, documentHeight: height }));
  }, [recordSnapshot]);

  const setDocumentBgColor = useCallback((color: string) => {
    setState((prev) => ({ ...prev, documentBgColor: color }));
  }, []);

  // ── Snap to grid ──────────────────────────────────────────────────────────

  const setSnapToGrid = useCallback((on: boolean) => {
    setState((prev) => ({ ...prev, snapToGrid: on }));
  }, []);

  // ── Image placement ───────────────────────────────────────────────────────

  const placeImageOnNewLayer = useCallback((base64: string, x: number, y: number, width: number, height: number) => {
    setState((prev) => {
      const newLayerId = nextLayerId();
      const newImage: ImageNode = {
        id: nextImageId(),
        x, y, width, height,
        src: base64.startsWith("data:") ? base64 : `data:image/png;base64,${base64}`,
      };
      const newLayer: CanvasLayer = {
        id: newLayerId,
        name: `Image ${prev.layers.length + 1}`,
        visible: true,
        opacity: 1,
        filters: [],
        images: [newImage],
        strokes: [],
        offsetX: 0,
        offsetY: 0,
        parentGroupId: null,
      };
      const next = { ...prev, layers: [...prev.layers, newLayer], activeLayerId: newLayerId };
      const { history, historyIndex } = pushHistory(prev.history, prev.historyIndex, serialize(next));
      return { ...next, history, historyIndex };
    });
  }, []);

  const placeImage = useCallback((base64: string, x: number, y: number, width: number, height: number) => {
    setState((prev) => {
      const activeIdx = prev.layers.findIndex((l) => l.id === prev.activeLayerId);
      if (activeIdx === -1) return prev;
      const newImage: ImageNode = {
        id: nextImageId(),
        x,
        y,
        width,
        height,
        src: base64.startsWith("data:") ? base64 : `data:image/png;base64,${base64}`,
      };
      const layers = prev.layers.map((l, i) =>
        i === activeIdx ? { ...l, images: [...l.images, newImage] } : l,
      );
      return recordSnapshot({ ...prev, layers });
    });
  }, [recordSnapshot]);

  const moveImage = useCallback((layerId: string, imageId: string, x: number, y: number) => {
    setState((prev) => ({
      ...prev,
      layers: prev.layers.map((l) =>
        l.id !== layerId
          ? l
          : { ...l, images: l.images.map((img) => (img.id === imageId ? { ...img, x, y } : img)) },
      ),
    }));
  }, []);

  // ── Strokes ───────────────────────────────────────────────────────────────

  const addStroke = useCallback((stroke: Omit<StrokeNode, "id">) => {
    setState((prev) => {
      const activeIdx = prev.layers.findIndex((l) => l.id === prev.activeLayerId);
      if (activeIdx === -1) return prev;
      const newStroke: StrokeNode = { ...stroke, id: nextStrokeId() };
      const layers = prev.layers.map((l, i) =>
        i === activeIdx ? { ...l, strokes: [...l.strokes, newStroke] } : l,
      );
      const next = { ...prev, layers };
      const { history, historyIndex } = pushHistory(prev.history, prev.historyIndex, serialize(next));
      return { ...next, history, historyIndex };
    });
  }, []);

  const addMaskStroke = useCallback((stroke: Omit<StrokeNode, "id">) => {
    setState((prev) => {
      const newStroke: StrokeNode = { ...stroke, id: nextStrokeId() };
      const next = { ...prev, maskStrokes: [...prev.maskStrokes, newStroke] };
      const { history, historyIndex } = pushHistory(prev.history, prev.historyIndex, serialize(next));
      return { ...next, history, historyIndex };
    });
  }, []);

  const clearMask = useCallback(() => {
    setState((prev) => {
      const next = { ...prev, maskStrokes: [] };
      const { history, historyIndex } = pushHistory(prev.history, prev.historyIndex, serialize(next));
      return { ...next, history, historyIndex };
    });
  }, []);

  // ── Filters ───────────────────────────────────────────────────────────────

  const setLayerFilters = useCallback((id: string, filters: FilterConfig[]) => {
    setState((prev) => ({
      ...prev,
      layers: prev.layers.map((l) => (l.id === id ? { ...l, filters } : l)),
    }));
  }, []);

  // ── Undo / Redo ───────────────────────────────────────────────────────────

  const parseSnapshot = (json: string): Partial<CanvasState> => {
    try { return JSON.parse(json); } catch { return {}; }
  };

  const undo = useCallback(() => {
    setState((prev) => {
      if (prev.historyIndex <= 0) return prev;
      const newIndex = prev.historyIndex - 1;
      return { ...prev, ...parseSnapshot(prev.history[newIndex]), historyIndex: newIndex };
    });
  }, []);

  const redo = useCallback(() => {
    setState((prev) => {
      if (prev.historyIndex >= prev.history.length - 1) return prev;
      const newIndex = prev.historyIndex + 1;
      return { ...prev, ...parseSnapshot(prev.history[newIndex]), historyIndex: newIndex };
    });
  }, []);

  // ── Serialization ─────────────────────────────────────────────────────────

  const getSerializedState = useCallback((): CanvasState => state, [state]);

  /** Return state without history, suitable for backend / cross-session storage. */
  const getPersistableState = useCallback(() => {
    const { history, historyIndex, ...rest } = state;
    return rest;
  }, [state]);

  const loadFromJSON = useCallback((json: string) => {
    try {
      const data = JSON.parse(json);
      // Advance counters past any IDs in the loaded data so newly created
      // strokes/images/layers/groups don't collide with loaded ones.
      advanceCountersFromState(data);
      setState((prev) => ({
        ...prev,
        layerGroups: data.layerGroups ?? prev.layerGroups,
        layers: (data.layers || prev.layers).map((l: CanvasLayer) => ({
          ...l,
          offsetX: l.offsetX ?? 0,
          offsetY: l.offsetY ?? 0,
          parentGroupId: l.parentGroupId ?? null,
        })),
        activeLayerId: data.activeLayerId ?? prev.activeLayerId,
        selectedLayerIds: data.selectedLayerIds ?? prev.selectedLayerIds,
        activeGridArea: data.activeGridArea || prev.activeGridArea,
        activeTool: data.activeTool || "brush",
        brushSize: data.brushSize ?? prev.brushSize,
        brushColor: data.brushColor || prev.brushColor,
        maskStrokes: data.maskStrokes || [],
        documentWidth: data.documentWidth ?? prev.documentWidth,
        documentHeight: data.documentHeight ?? prev.documentHeight,
        documentBgColor: data.documentBgColor ?? prev.documentBgColor,
        snapToGrid: data.snapToGrid ?? prev.snapToGrid,
      }));
    } catch { /* ignore */ }
  }, []);

  // ── Brush controls ────────────────────────────────────────────────────────

  const setBrushSize = useCallback((size: number) => {
    setState((prev) => ({ ...prev, brushSize: Math.max(1, size) }));
  }, []);

  const setBrushColor = useCallback((color: string) => {
    setState((prev) => ({ ...prev, brushColor: color }));
  }, []);

  // ── Derived ───────────────────────────────────────────────────────────────

  const activeLayer = useMemo(
    () => state.layers.find((l) => l.id === state.activeLayerId) ?? null,
    [state.layers, state.activeLayerId],
  );

  return {
    ...state,
    activeLayer,
    addLayer,
    deleteLayer,
    renameLayer,
    setLayerVisible,
    setLayerOpacity,
    reorderLayer,
    reorderLayerToIndex,
    setActiveLayer,
    toggleLayerSelection,
    selectLayerRange,
    mergeSelectedLayers,
    addLayerGroup,
    toggleGroupExpanded,
    renameGroup,
    deleteGroup,
    moveLayerToGroup,
    setActiveTool,
    setActiveGridArea,
    resetDocument,
    moveLayer,
    setDocumentSize,
    setDocumentBgColor,
    setSnapToGrid,
    placeImageOnNewLayer,
    placeImage,
    moveImage,
    addStroke,
    addMaskStroke,
    clearMask,
    setLayerFilters,
    undo,
    redo,
    getSerializedState,
    getPersistableState,
    loadFromJSON,
    setBrushSize,
    setBrushColor,
  };
}

export type CanvasActions = ReturnType<typeof useCanvasState>;
