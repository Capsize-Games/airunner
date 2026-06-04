import { createContext, useContext, type ReactNode } from "react";
import { useCanvasState } from "./useCanvasState";
import type {
  CanvasLayer,
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
  activeLayerId: string | null;
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
  setActiveLayer: (id: string) => void;
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
