// ── Canvas Types ─────────────────────────────────────────────────────────────

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

export interface TextNodeData {
  text: string;
  x: number;
  y: number;
  fontFamily: string;
  fontSize: number;
  fill: string;
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
  fillColor?: string; // hex or 'transparent', rendered as background
  maskStrokes?: StrokeNode[] | null; // null/undefined = no mask; array = mask exists (white = show, black = hide)
  maskFill?: "white" | "black";      // background of the mask: white = fully visible, black = fully hidden
  maskTarget?: "content" | "mask";   // which target receives strokes (default "content")
  textNode?: TextNodeData;           // text tool output — one text node per layer
}

export interface LayerGroup {
  id: string;
  name: string;
  expanded: boolean;
  visible: boolean;
  opacity: number; // 0–1
}

export interface ActiveGridArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type ActiveTool =
  | "select" | "brush" | "eraser" | "mask" | "move"
  | "lasso" | "wand" | "crop" | "bucket" | "smudge"
  | "text" | "pipette" | "zoom" | "grid";

export type ZoomDirection = "in" | "out";

export type MoveMode = "pick" | "move-selected";

export interface CanvasState {
  /** Monotonic timestamp (Date.now()) used to resolve localStorage vs server
   *  conflicts on reload.  The source with the higher _ts wins. */
  _ts: number;
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string; // hex or 'transparent'
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  /** Interleaved order of group IDs and ungrouped layer IDs for display.
   *  Bottom-first (index 0 = bottom of stack).
   *  When a group is expanded, its children follow the group header. */
  displayOrder: string[];
  activeLayerId: string | null;
  selectedLayerIds: string[];
  activeGridArea: ActiveGridArea;
  activeTool: ActiveTool;
  moveMode: MoveMode;
  brushSize: number;
  brushColor: string;
  lassoAntialiasing: boolean;
  lassoFeatherEdges: boolean;
  lassoFeatherRadius: number; // 0–100
  wandAntialiasing: boolean;
  wandFeatherEdges: boolean;
  wandFeatherRadius: number; // 0–100
  wandSelectTransparentAreas: boolean;
  wandSampleMerged: boolean;
  wandDiagonalNeighbors: boolean;
  wandThreshold: number; // 0–100, mapped to RGBA distance
  bucketColorSource: "foreground" | "background";
  bucketFillTransparentAreas: boolean;
  bucketAntialiasing: boolean;
  bucketThreshold: number; // 0–100
  smudgeSize: number; // 0–100
  pipetteTarget: "foreground" | "background";
  textFont: string;
  textSize: number;
  textColor: string;
  maskStrokes: StrokeNode[];
  snapToGrid: boolean;
  cropX: number;
  cropY: number;
  cropWidth: number;
  cropHeight: number;
  gridShowGrid: boolean;
  gridSize: number;
  gridColor: string;
  zoomDirection: ZoomDirection;
  history: string[];
  historyIndex: number;
}
