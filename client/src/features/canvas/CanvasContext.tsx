import { createContext, useContext, type ReactNode } from "react";
import { useCanvasState } from "./useCanvasState";
import type {
  CanvasLayer,
  LayerGroup,
  ActiveGridArea,
  StrokeNode,
  FilterConfig,
  CanvasState,
  ActiveTool,
  MoveMode,
} from "./useCanvasState";
import type { TextNodeData, SelectionData } from "./canvasTypes";

export interface CanvasContextValue {
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  displayOrder: string[];
  activeLayerId: string | null;
  selectedLayerIds: string[];
  selection: SelectionData | null;
  activeLayer: CanvasLayer | null;
  activeGridArea: ActiveGridArea;
  activeTool: ActiveTool;
  moveMode: MoveMode;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  inpaintMaskStrokes: StrokeNode[];
  snapToGrid: boolean;

  addInpaintMaskStroke: (stroke: Omit<StrokeNode, "id">) => void;
  clearInpaintMask: () => void;

  addLayer: (name?: string, opacity?: number, fillColor?: string) => void;
  deleteLayer: (id: string) => void;
  renameLayer: (id: string, name: string) => void;
  setLayerVisible: (id: string, visible: boolean) => void;
  setLayerOpacity: (id: string, opacity: number) => void;
  setLayerFillColor: (id: string, fillColor: string) => void;
  reorderLayer: (id: string, direction: "up" | "down") => void;
  reorderLayerToIndex: (id: string, toIndex: number) => void;
  setActiveLayer: (id: string) => void;
  setSelection: (points: number[], feather?: number, antialias?: boolean) => void;
  clearSelection: () => void;
  selectAll: () => void;
  resetToolPresets: (tool: ActiveTool) => void;
  resetAllToolPresets: () => void;
  toggleLayerSelection: (id: string) => void;
  mergeSelectedLayers: () => void;
  selectLayerRange: (id: string) => void;
  addLayerGroup: () => void;
  toggleGroupExpanded: (id: string) => void;
  renameGroup: (id: string, name: string) => void;
  deleteGroup: (id: string) => void;
  setGroupVisible: (id: string, visible: boolean) => void;
  setGroupOpacity: (id: string, opacity: number) => void;
  moveLayerToGroup: (layerId: string, groupId: string | null, toIndex?: number) => void;
  reorderDisplayItem: (id: string, toIndex: number) => void;
  setActiveTool: (tool: ActiveTool) => void;
  setMoveMode: (mode: MoveMode) => void;
  setActiveGridArea: (area: ActiveGridArea) => void;
  resetDocument: (fillColor?: string) => void;
  moveLayer: (id: string, x: number, y: number) => void;
  setDocumentSize: (width: number, height: number) => void;
  setDocumentBgColor: (color: string) => void;
  setSnapToGrid: (on: boolean) => void;
  placeImageOnNewLayer: (base64: string, x: number, y: number, width: number, height: number) => void;
  placeImage: (base64: string, x: number, y: number, width: number, height: number) => void;
  moveImage: (layerId: string, imageId: string, x: number, y: number) => void;
  updateImageSrc: (layerId: string, imageId: string, src: string) => void;
  addStroke: (stroke: Omit<StrokeNode, "id">) => void;
  addMaskStroke: (stroke: Omit<StrokeNode, "id">) => void;
  clearMask: () => void;
  addLayerMask: (layerId: string, fill?: "white" | "black") => void;
  removeLayerMask: (layerId: string) => void;
  addLayerMaskStroke: (layerId: string, stroke: Omit<StrokeNode, "id">) => void;
  setLayerMaskTarget: (layerId: string, target: "content" | "mask") => void;
  setLayerFilters: (id: string, filters: FilterConfig[]) => void;
  undo: () => void;
  redo: () => void;
  getSerializedState: () => CanvasState;
  getPersistableState: () => Omit<CanvasState, "history" | "historyIndex">;
  loadFromJSON: (json: string) => void;
  setBrushSize: (size: number) => void;
  setBrushColor: (color: string) => void;
  // ── Wand tool settings ─────────────────────────────────────────────
  wandAntialiasing: boolean;
  wandFeatherEdges: boolean;
  wandFeatherRadius: number;
  wandSelectTransparentAreas: boolean;
  wandSampleMerged: boolean;
  wandDiagonalNeighbors: boolean;
  wandThreshold: number;
  setWandAntialiasing: (value: boolean) => void;
  setWandFeatherEdges: (value: boolean) => void;
  setWandFeatherRadius: (value: number) => void;
  setWandSelectTransparentAreas: (value: boolean) => void;
  setWandSampleMerged: (value: boolean) => void;
  setWandDiagonalNeighbors: (value: boolean) => void;
  setWandThreshold: (value: number) => void;
  // ── Bucket tool settings ───────────────────────────────────────────
  bucketColorSource: "foreground" | "background";
  bucketFillTransparentAreas: boolean;
  bucketAntialiasing: boolean;
  bucketThreshold: number;
  setBucketColorSource: (value: "foreground" | "background") => void;
  setBucketFillTransparentAreas: (value: boolean) => void;
  setBucketAntialiasing: (value: boolean) => void;
  setBucketThreshold: (value: number) => void;
  // ── Lasso tool settings (also exposed via context) ──────────────────
  lassoAntialiasing: boolean;
  lassoFeatherEdges: boolean;
  lassoFeatherRadius: number;
  setLassoAntialiasing: (value: boolean) => void;
  setLassoFeatherEdges: (value: boolean) => void;
  setLassoFeatherRadius: (value: number) => void;
  // ── Crop tool settings ─────────────────────────────────────────────
  cropX: number;
  cropY: number;
  cropWidth: number;
  cropHeight: number;
  setCropX: (value: number) => void;
  setCropY: (value: number) => void;
  setCropWidth: (value: number) => void;
  setCropHeight: (value: number) => void;
  // ── Smudge tool settings ─────────────────────────────────────────────
  smudgeSize: number;
  setSmudgeSize: (value: number) => void;
  // ── Pipette (Color Picker) settings ──────────────────────────────────
  pipetteTarget: "foreground" | "background";
  setPipetteTarget: (value: "foreground" | "background") => void;
  // ── Zoom tool settings ──────────────────────────────────────────────
  zoomDirection: "in" | "out";
  setZoomDirection: (value: "in" | "out") => void;
  // ── Grid tool settings ──────────────────────────────────────────────
  gridShowGrid: boolean;
  gridSize: number;
  gridColor: string;
  setGridShowGrid: (value: boolean) => void;
  setGridSize: (value: number) => void;
  setGridColor: (value: string) => void;
  // ── Ruler tool settings ─────────────────────────────────────────────
  rulerShowRuler: boolean;
  setRulerShowRuler: (value: boolean) => void;
  // ── Text tool settings ──────────────────────────────────────────────
  textFont: string;
  textSize: number;
  textColor: string;
  setTextFont: (value: string) => void;
  setTextSize: (value: number) => void;
  setTextColor: (value: string) => void;
  // ── Text tool layer management ──────────────────────────────────────
  setTextNode: (layerId: string, textNode: TextNodeData) => void;
}

const CanvasContext = createContext<CanvasContextValue | null>(null);

export function CanvasProvider({ children }: { children: ReactNode }) {
  const canvas = useCanvasState();
  return (
    <CanvasContext.Provider value={canvas as unknown as CanvasContextValue}>
      {children}
    </CanvasContext.Provider>
  );
}

export function useCanvasContext(): CanvasContextValue {
  const ctx = useContext(CanvasContext);
  if (!ctx) throw new Error("useCanvasContext must be used within a CanvasProvider");
  return ctx;
}
