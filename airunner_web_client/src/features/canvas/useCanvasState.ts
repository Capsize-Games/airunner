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
  activeLayerId: string | null;
  activeGridArea: ActiveGridArea;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  snapToGrid: boolean;
  history: string[];
  historyIndex: number;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

let _layerIdCounter = 0;
const nextLayerId = (): string => `layer_${++_layerIdCounter}`;
let _strokeIdCounter = 0;
const nextStrokeId = (): string => `stroke_${++_strokeIdCounter}`;
let _imageIdCounter = 0;
const nextImageId = (): string => `image_${++_imageIdCounter}`;

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
      },
    ],
    activeLayerId: firstId,
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
      return recordSnapshot({ ...prev, layers: filtered, activeLayerId: newActive });
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
    setState((prev) => ({ ...prev, activeLayerId: id }));
  }, []);

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
      setState((prev) => ({
        ...prev,
        layers: (data.layers || prev.layers).map((l: CanvasLayer) => ({
          ...l,
          offsetX: l.offsetX ?? 0,
          offsetY: l.offsetY ?? 0,
        })),
        activeLayerId: data.activeLayerId ?? prev.activeLayerId,
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
    setActiveLayer,
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
