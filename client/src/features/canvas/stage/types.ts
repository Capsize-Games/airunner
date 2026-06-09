// ── Canvas Stage Types ──────────────────────────────────────────────────
import Konva from "konva";
import type {
  CanvasLayer,
  ActiveGridArea,
  StrokeNode,
  ActiveTool,
  LayerGroup,
} from "../useCanvasState";
import type {
  LiveStrokeMessage,
  StrokeEndMessage,
} from "../canvasSyncTypes";

export const GRID_SIZE = 16;

export interface CanvasStageHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  zoomReset: () => void;
  centerView: () => void;
  fitView: () => void;
  getZoom: () => number;
  getStage: () => Konva.Stage | null;
}

export interface CanvasStageProps {
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  displayOrder: string[];
  activeLayerId: string | null;
  activeGridArea: ActiveGridArea;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  showGrid: boolean;
  snapToGrid: boolean;
  onAddStroke: (
    stroke: Omit<StrokeNode, "id">,
  ) => void;
  onMoveImage: (
    layerId: string,
    imageId: string,
    x: number,
    y: number,
  ) => void;
  onMoveLayer: (
    layerId: string,
    x: number,
    y: number,
  ) => void;
  onAddMaskStroke: (
    stroke: Omit<StrokeNode, "id">,
  ) => void;
  onAddLayerMaskStroke: (
    layerId: string,
    stroke: Omit<StrokeNode, "id">,
  ) => void;
  setActiveGridArea: (area: ActiveGridArea) => void;
  onUndo: () => void;
  onRedo: () => void;
  setActiveTool: (tool: ActiveTool) => void;
  onZoomChange: (zoom: number) => void;
  isFitToView: boolean;
  isCenterView: boolean;
  onFitToViewChange: (v: boolean) => void;
  onCenterViewChange: (v: boolean) => void;
  gridLayerRef: React.RefObject<Konva.Layer>;
  maskLayerRef: React.RefObject<Konva.Layer>;
  stageRef: React.RefObject<Konva.Stage>;
  ghostLayerRef: React.RefObject<Konva.Layer | null>;
  sendLiveStroke?: (msg: LiveStrokeMessage) => void;
  sendStrokeEnd?: (msg: StrokeEndMessage) => void;
}
