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
} from "./useCanvasState";

export interface CanvasContextValue {
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  activeLayerId: string | null;
  selectedLayerIds: string[];
  activeLayer: CanvasLayer | null;
  activeGridArea: ActiveGridArea;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  snapToGrid: boolean;

  addLayer: () => void;
  deleteLayer: (id: string) => void;
  renameLayer: (id: string, name: string) => void;
  setLayerVisible: (id: string, visible: boolean) => void;
  setLayerOpacity: (id: string, opacity: number) => void;
  reorderLayer: (id: string, direction: "up" | "down") => void;
  reorderLayerToIndex: (id: string, toIndex: number) => void;
  setActiveLayer: (id: string) => void;
  toggleLayerSelection: (id: string) => void;
  mergeSelectedLayers: () => void;
  selectLayerRange: (id: string) => void;
  addLayerGroup: () => void;
  toggleGroupExpanded: (id: string) => void;
  renameGroup: (id: string, name: string) => void;
  deleteGroup: (id: string) => void;
  moveLayerToGroup: (layerId: string, groupId: string | null) => void;
  setActiveTool: (tool: ActiveTool) => void;
  setActiveGridArea: (area: ActiveGridArea) => void;
  resetDocument: () => void;
  moveLayer: (id: string, x: number, y: number) => void;
  setDocumentSize: (width: number, height: number) => void;
  setDocumentBgColor: (color: string) => void;
  setSnapToGrid: (on: boolean) => void;
  placeImageOnNewLayer: (base64: string, x: number, y: number, width: number, height: number) => void;
  placeImage: (base64: string, x: number, y: number, width: number, height: number) => void;
  moveImage: (layerId: string, imageId: string, x: number, y: number) => void;
  addStroke: (stroke: Omit<StrokeNode, "id">) => void;
  addMaskStroke: (stroke: Omit<StrokeNode, "id">) => void;
  clearMask: () => void;
  setLayerFilters: (id: string, filters: FilterConfig[]) => void;
  undo: () => void;
  redo: () => void;
  getSerializedState: () => CanvasState;
  getPersistableState: () => Omit<CanvasState, "history" | "historyIndex">;
  loadFromJSON: (json: string) => void;
  setBrushSize: (size: number) => void;
  setBrushColor: (color: string) => void;
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
