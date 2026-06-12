// ── Canvas Stage Types ──────────────────────────────────────────────────
import Konva from "konva";
import type {
  CanvasLayer,
  ActiveGridArea,
  StrokeNode,
  ActiveTool,
  MoveMode,
  LayerGroup,
} from "../useCanvasState";
import type {
  LiveStrokeMessage,
  StrokeEndMessage,
} from "../canvasSyncTypes";

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
  moveMode: MoveMode;
  selectedLayerIds: string[];
  maskStrokes: StrokeNode[];
  inpaintMaskStrokes: StrokeNode[];
  /** Current generation type — drives the active generation area + inpaint mask
   *  overlays. Undefined outside the image-generation canvas. */
  generationType?: "txt2img" | "img2img" | "inpaint";
  showGrid: boolean;
  gridSize: number;
  gridColor: string;
  showRuler: boolean;
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
  onAddInpaintMaskStroke: (
    stroke: Omit<StrokeNode, "id">,
  ) => void;
  setActiveGridArea: (area: ActiveGridArea) => void;
  onUndo: () => void;
  onRedo: () => void;
  setActiveTool: (tool: ActiveTool) => void;
  setActiveLayer: (layerId: string) => void;
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
