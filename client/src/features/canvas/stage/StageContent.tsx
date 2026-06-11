// ── Canvas Stage Content ─────────────────────────────────────────────────────
// JSX-only rendering of the Konva Stage and all its layers.
// No interaction logic lives here — each tool's rendering is delegated to its
// own <ToolLayer> component imported from stage/tools/<tool>/.
//
// To add a new tool overlay:
//   import <Tool>Layer from "./tools/<tool>/<Tool>Layer";
//   Add renderState prop to Props
//   Render <ToolLayer> conditionally inside <Stage>

import { useMemo } from "react";
import { Stage, Layer, Rect, Circle } from "react-konva";
import Konva from "konva";
import CanvasLayerRenderer from "../CanvasLayer";
import MaskLayer from "../MaskLayer";
import CanvasBackground from "../CanvasBackground";
import GridLayer from "./GridLayer";
import LassoLayer from "./tools/lasso/LassoLayer";
import SelectLayer from "./tools/select/SelectLayer";
import WandLayer from "./tools/wand/WandLayer";
import CropLayer from "./tools/crop/CropLayer";
import SelectionOverlay from "./SelectionOverlay";
import BucketLayer from "./tools/bucket/BucketLayer";
import SmudgeLayer from "./tools/smudge/SmudgeLayer";
import PipetteLayer from "./tools/pipette/PipetteLayer";
import ZoomLayer from "./tools/zoom/ZoomLayer";
import TextLayer from "./tools/text/TextLayer";
import type { LassoRenderState } from "./tools/lasso/useLassoTool";
import type { SelectRenderState } from "./tools/select/useSelectTool";
import type { WandRenderState } from "./tools/wand/useWandTool";
import type { CropRenderState } from "./tools/crop/useCropTool";
import type { BucketRenderState } from "./tools/bucket/useBucketTool";
import type { SmudgeRenderState } from "./tools/smudge/useSmudgeTool";
import type { PipetteRenderState } from "./tools/pipette/usePipetteTool";
import type { ZoomRenderState } from "./tools/zoom/useZoomTool";
import type { TextRenderState } from "./tools/text/useTextTool";
import type {
  CanvasLayer,
  LayerGroup,
  ActiveTool,
  StrokeNode,
  MoveMode,
} from "../useCanvasState";
import type { SelectionData } from "../canvasTypes";

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  stageRef: React.RefObject<Konva.Stage>;
  gridLayerRef: React.RefObject<Konva.Layer>;
  maskLayerRef: React.RefObject<Konva.Layer>;
  ghostLayerRef: React.RefObject<Konva.Layer | null>;
  stageSize: { width: number; height: number };
  /** Current stage zoom — used to keep UI chrome a constant on-screen size. */
  zoom: number;
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  displayOrder: string[];
  activeLayerId: string | null;
  activeTool: ActiveTool;
  moveMode: MoveMode;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  showGrid: boolean;
  gridSize: number;
  gridColor: string;
  snapToGrid: boolean;
  /** Committed, tool-independent selection (drives the marching-ants overlay). */
  selection: SelectionData | null;
  // ── Tool render states (one per tool with a visual overlay) ─────────────
  lassoRenderState: LassoRenderState;
  selectRenderState: SelectRenderState;
  wandRenderState: WandRenderState;
  cropRenderState: CropRenderState;
  bucketRenderState: BucketRenderState;
  smudgeRenderState: SmudgeRenderState;
  pipetteRenderState: PipetteRenderState;
  zoomToolRenderState: ZoomRenderState;
  textToolRenderState: TextRenderState;
  cropOnRectChange: (
    x: number, y: number,
    width: number, height: number,
  ) => void;
  // ── Drawing overlay ──────────────────────────────────────────────────────
  showBrushIndicator: boolean;
  brushRadius: number;
  indicatorColor: string;
  brushRingRef: React.RefObject<Konva.Circle | null>;
  brushDotRef: React.RefObject<Konva.Circle | null>;
  brushIndicatorLayerRef: React.RefObject<Konva.Layer | null>;
  isDrawingTool: boolean;
  drawingOffsetX: number;
  drawingOffsetY: number;
  // ── Event handlers ───────────────────────────────────────────────────────
  handleWheel:     (e: Konva.KonvaEventObject<WheelEvent>)   => void;
  handleMouseDown: (e: Konva.KonvaEventObject<MouseEvent>)   => void;
  handleMouseMove: (e: Konva.KonvaEventObject<MouseEvent>)   => void;
  handleMouseUp:   (e: Konva.KonvaEventObject<MouseEvent>)   => void;
  handleOverlayPointerDown: (e: Konva.KonvaEventObject<PointerEvent>) => void;
  handleOverlayPointerMove: (e: Konva.KonvaEventObject<PointerEvent>) => void;
  handleOverlayPointerUp:   (e: Konva.KonvaEventObject<PointerEvent>) => void;
  updateBrushIndicator: (pos: { x: number; y: number } | null) => void;
  // ── Data callbacks ───────────────────────────────────────────────────────
  onAddStroke:         (stroke: Omit<StrokeNode, "id">) => void;
  onMoveImage:         (layerId: string, imageId: string, x: number, y: number) => void;
  onMoveLayer:         (layerId: string, x: number, y: number) => void;
  onAddMaskStroke:     (stroke: Omit<StrokeNode, "id">) => void;
  onAddLayerMaskStroke:(layerId: string, stroke: Omit<StrokeNode, "id">) => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function StageContent({
  stageRef, gridLayerRef, maskLayerRef, ghostLayerRef,
  stageSize, zoom, documentWidth, documentHeight, documentBgColor,
  layers, layerGroups, displayOrder, activeLayerId,
  activeTool, moveMode, brushSize, brushColor, maskStrokes,
  showGrid, gridSize, gridColor, snapToGrid,
  selection,
  lassoRenderState, selectRenderState, wandRenderState,
  cropRenderState, bucketRenderState, smudgeRenderState,
  pipetteRenderState, zoomToolRenderState, textToolRenderState,
  cropOnRectChange,
  showBrushIndicator, brushRadius, indicatorColor,
  brushRingRef, brushDotRef, brushIndicatorLayerRef,
  isDrawingTool,
  handleWheel, handleMouseDown, handleMouseMove, handleMouseUp,
  handleOverlayPointerDown, handleOverlayPointerMove, handleOverlayPointerUp,
  updateBrushIndicator,
  onAddStroke, onMoveImage, onMoveLayer, onAddMaskStroke, onAddLayerMaskStroke,
}: Props) {

  // Flatten displayOrder into an ordered CanvasLayer list
  const orderedLayers = useMemo(() => {
    const result: CanvasLayer[] = [];
    const seen = new Set<string>();
    for (const id of displayOrder) {
      const group = layerGroups.find((g) => g.id === id);
      if (group) {
        for (const child of layers.filter((l) => l.parentGroupId === id)) {
          if (!seen.has(child.id)) { result.push(child); seen.add(child.id); }
        }
        continue;
      }
      const layer = layers.find((l) => l.id === id);
      if (layer && !seen.has(layer.id)) { result.push(layer); seen.add(layer.id); }
    }
    for (const layer of layers) {
      if (!seen.has(layer.id)) { result.push(layer); seen.add(layer.id); }
    }
    return result;
  }, [displayOrder, layerGroups, layers]);

  return (
    <Stage
      width={stageSize.width}
      height={stageSize.height}
      ref={stageRef}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={() => updateBrushIndicator(null)}
      onMouseEnter={() => {
        const stage = stageRef.current;
        if (!stage) return;
        const raw = stage.getPointerPosition();
        if (raw) {
          const doc = stage.getAbsoluteTransform().copy().invert().point(raw);
          updateBrushIndicator(doc);
        }
      }}
      style={{ display: "block" }}
    >
      {/* ── Document background ────────────────────────────────────────── */}
      <CanvasBackground
        documentWidth={documentWidth}
        documentHeight={documentHeight}
        documentBgColor={documentBgColor}
      />

      {/* ── Canvas layers ──────────────────────────────────────────────── */}
      {orderedLayers.map((layer, index) => {
        const isMaskTarget =
          layer.id === activeLayerId &&
          Array.isArray(layer.maskStrokes) &&
          layer.maskTarget === "mask";
        return (
          <CanvasLayerRenderer
            key={layer.id ?? `layer-${index}`}
            layer={layer}
            isActive={layer.id === activeLayerId}
            activeTool={activeTool}
            moveMode={moveMode}
            brushSize={brushSize}
            brushColor={brushColor}
            snapToGrid={snapToGrid}
            gridSize={gridSize}
            canvasWidth={documentWidth}
            canvasHeight={documentHeight}
            onStrokeComplete={
              isMaskTarget
                ? (stroke) => onAddLayerMaskStroke(layer.id, stroke)
                : onAddStroke
            }
            onMoveImage={onMoveImage}
            onMoveLayer={onMoveLayer}
          />
        );
      })}

      {/* ── Drawing overlay (brush / eraser pointer capture) ───────────── */}
      {isDrawingTool && activeLayerId && (
        <Layer listening={true}>
          <Rect
            x={-50000} y={-50000} width={100000} height={100000}
            fill="transparent"
            onPointerDown={handleOverlayPointerDown}
            onPointerMove={handleOverlayPointerMove}
            onPointerUp={handleOverlayPointerUp}
          />
        </Layer>
      )}

      {/* ── Grid ───────────────────────────────────────────────────────── */}
      <Layer listening={false} visible={showGrid}>
        <GridLayer
          documentWidth={documentWidth}
          documentHeight={documentHeight}
          gridSize={gridSize}
          gridColor={gridColor}
        />
      </Layer>
      <Layer ref={gridLayerRef}  listening={false} visible={false} />
      <Layer ref={ghostLayerRef} listening={false} />

      {/* ── Mask layer ─────────────────────────────────────────────────── */}
      {activeTool === "mask" && (() => {
        const activeLayer = layers.find((l) => l.id === activeLayerId) ?? null;
        const hasLayerMask = Array.isArray(activeLayer?.maskStrokes);
        const handleMaskStroke =
          hasLayerMask && activeLayerId
            ? (stroke: Omit<StrokeNode, "id">) => onAddLayerMaskStroke(activeLayerId, stroke)
            : onAddMaskStroke;
        const visibleStrokes = hasLayerMask
          ? (activeLayer?.maskStrokes ?? [])
          : maskStrokes;
        return (
          <Layer ref={maskLayerRef}>
            <MaskLayer
              strokes={visibleStrokes}
              activeTool={activeTool}
              brushSize={brushSize}
              documentWidth={documentWidth}
              documentHeight={documentHeight}
              onStrokeComplete={handleMaskStroke}
            />
          </Layer>
        );
      })()}

      {/* ── Brush / eraser indicator ────────────────────────────────────── */}
      {showBrushIndicator && (
        <Layer listening={false} ref={brushIndicatorLayerRef}>
          <Circle
            ref={brushRingRef}
            radius={brushRadius}
            fill="transparent"
            stroke={indicatorColor}
            strokeWidth={2}
            strokeScaleEnabled={false}
            visible={false}
          />
          {/* Center dot — a fixed-size pointer marker (divide by zoom so the
              layer's scale leaves it constant on screen). */}
          <Circle
            ref={brushDotRef}
            radius={1.5 / zoom}
            fill={indicatorColor}
            visible={false}
          />
        </Layer>
      )}

      {/* ── Tool overlays ──────────────────────────────────────────────── */}
      {/* Each tool renders its own Konva layer(s) when active.            */}
      {/* Add new tools here following the same pattern.                   */}

      {activeTool === "select" && (
        <SelectLayer {...selectRenderState} zoom={zoom} />
      )}

      {activeTool === "lasso" && (
        <LassoLayer {...lassoRenderState} zoom={zoom} />
      )}

      {activeTool === "wand" && (
        <WandLayer {...wandRenderState} />
      )}

      {activeTool === "crop" && (
        <CropLayer
          {...cropRenderState}
          documentWidth={documentWidth}
          documentHeight={documentHeight}
          onCropRectChange={cropOnRectChange}
        />
      )}

      {/* Persistent selection (marching ants) — visible under every tool. */}
      <SelectionOverlay selection={selection} />
{activeTool === "bucket" && (
  <BucketLayer {...bucketRenderState} />
)}

{activeTool === "smudge" && (
  <SmudgeLayer {...smudgeRenderState} />
)}

{activeTool === "pipette" && (
  <PipetteLayer {...pipetteRenderState} />
)}

{activeTool === "zoom" && (
  <ZoomLayer {...zoomToolRenderState} />
)}

{activeTool === "text" && (
  <TextLayer {...textToolRenderState} />
)}

    </Stage>
  );
}
