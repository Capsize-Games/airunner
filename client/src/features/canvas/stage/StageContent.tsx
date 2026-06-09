// ── Canvas Stage Content ────────────────────────────────────────────────
// JSX rendering of the Stage and all its layers.
// Extracted from CanvasStage to keep the parent under 250 lines.

import { useMemo } from "react";
import { Stage, Layer, Rect, Text, Circle } from "react-konva";
import Konva from "konva";
import CanvasLayerRenderer from "../CanvasLayer";
import MaskLayer from "../MaskLayer";
import CanvasBackground from "../CanvasBackground";
import GridLayer from "./GridLayer";
import type {
  CanvasLayer,
  LayerGroup,
  ActiveTool,
  StrokeNode,
} from "../useCanvasState";

interface Props {
  stageRef: React.RefObject<Konva.Stage>;
  gridLayerRef: React.RefObject<Konva.Layer>;
  maskLayerRef: React.RefObject<Konva.Layer>;
  ghostLayerRef: React.RefObject<Konva.Layer | null>;
  stageSize: { width: number; height: number };
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  displayOrder: string[];
  activeLayerId: string | null;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  showGrid: boolean;
  snapToGrid: boolean;
  selectionRect: {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null;
  showBrushIndicator: boolean;
  brushRadius: number;
  indicatorColor: string;
  brushRingRef: React.RefObject<Konva.Circle | null>;
  brushDotRef: React.RefObject<Konva.Circle | null>;
  brushIndicatorLayerRef: React.RefObject<Konva.Layer | null>;
  isDrawingTool: boolean;
  drawingOffsetX: number;
  drawingOffsetY: number;
  handleWheel: (
    e: Konva.KonvaEventObject<WheelEvent>,
  ) => void;
  handleMouseDown: (
    e: Konva.KonvaEventObject<MouseEvent>,
  ) => void;
  handleMouseMove: (
    e: Konva.KonvaEventObject<MouseEvent>,
  ) => void;
  handleMouseUp: (
    e: Konva.KonvaEventObject<MouseEvent>,
  ) => void;
  handleOverlayPointerDown: (
    e: Konva.KonvaEventObject<PointerEvent>,
  ) => void;
  handleOverlayPointerMove: (
    e: Konva.KonvaEventObject<PointerEvent>,
  ) => void;
  handleOverlayPointerUp: (
    e: Konva.KonvaEventObject<PointerEvent>,
  ) => void;
  updateBrushIndicator: (
    pos: { x: number; y: number } | null,
  ) => void;
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
}

export default function StageContent({
  stageRef,
  gridLayerRef,
  maskLayerRef,
  ghostLayerRef,
  stageSize,
  documentWidth,
  documentHeight,
  documentBgColor,
  layers,
  layerGroups,
  displayOrder,
  activeLayerId,
  activeTool,
  brushSize,
  brushColor,
  maskStrokes,
  showGrid,
  snapToGrid,
  selectionRect,
  showBrushIndicator,
  brushRadius,
  indicatorColor,
  brushRingRef,
  brushDotRef,
  brushIndicatorLayerRef,
  isDrawingTool,
  handleWheel,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  handleOverlayPointerDown,
  handleOverlayPointerMove,
  handleOverlayPointerUp,
  updateBrushIndicator,
  onAddStroke,
  onMoveImage,
  onMoveLayer,
  onAddMaskStroke,
  onAddLayerMaskStroke,
}: Props) {
  // Derive ordered layer list from displayOrder
  const orderedLayers = useMemo(() => {
    const result: CanvasLayer[] = [];
    const seen = new Set<string>();
    for (const id of displayOrder) {
      const group = layerGroups.find(
        (g) => g.id === id,
      );
      if (group) {
        const children = layers.filter(
          (l) => l.parentGroupId === id,
        );
        for (const child of children) {
          if (!seen.has(child.id)) {
            result.push(child);
            seen.add(child.id);
          }
        }
        continue;
      }
      const layer = layers.find((l) => l.id === id);
      if (layer && !seen.has(layer.id)) {
        result.push(layer);
        seen.add(layer.id);
      }
    }
    for (const layer of layers) {
      if (!seen.has(layer.id)) {
        result.push(layer);
        seen.add(layer.id);
      }
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
          const doc = stage
            .getAbsoluteTransform()
            .copy()
            .invert()
            .point(raw);
          updateBrushIndicator(doc);
        }
      }}
      style={{ display: "block" }}
    >
      <CanvasBackground
        documentWidth={documentWidth}
        documentHeight={documentHeight}
        documentBgColor={documentBgColor}
      />

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
            brushSize={brushSize}
            brushColor={brushColor}
            snapToGrid={snapToGrid}
            canvasWidth={documentWidth}
            canvasHeight={documentHeight}
            onStrokeComplete={
              isMaskTarget
                ? (stroke) =>
                    onAddLayerMaskStroke(
                      layer.id,
                      stroke,
                    )
                : onAddStroke
            }
            onMoveImage={onMoveImage}
            onMoveLayer={onMoveLayer}
          />
        );
      })}

      {isDrawingTool && activeLayerId && (
        <Layer listening={true}>
          <Rect
            x={-50000}
            y={-50000}
            width={100000}
            height={100000}
            fill="transparent"
            onPointerDown={handleOverlayPointerDown}
            onPointerMove={handleOverlayPointerMove}
            onPointerUp={handleOverlayPointerUp}
          />
        </Layer>
      )}

      <Layer listening={false} visible={showGrid}>
        <GridLayer
          documentWidth={documentWidth}
          documentHeight={documentHeight}
        />
      </Layer>

      <Layer
        ref={gridLayerRef}
        listening={false}
        visible={false}
      />

      <Layer
        ref={ghostLayerRef}
        listening={false}
      />

      {activeTool === "mask" &&
        (() => {
          const activeLayer =
            layers.find(
              (l) => l.id === activeLayerId,
            ) ?? null;
          const hasLayerMask = Array.isArray(
            activeLayer?.maskStrokes,
          );
          const handleMaskStroke =
            hasLayerMask && activeLayerId
              ? (stroke: Omit<StrokeNode, "id">) =>
                  onAddLayerMaskStroke(
                    activeLayerId,
                    stroke,
                  )
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

      {showBrushIndicator && (
        <Layer
          listening={false}
          ref={brushIndicatorLayerRef}
        >
          <Circle
            ref={brushRingRef}
            radius={brushRadius}
            fill="transparent"
            stroke={indicatorColor}
            strokeWidth={2 / (brushRadius > 0 ? 1 : 1)}
            visible={false}
          />
          <Circle
            ref={brushDotRef}
            radius={1.5}
            fill={indicatorColor}
            visible={false}
          />
        </Layer>
      )}

      {selectionRect && activeTool === "select" && (
        <>
          <Layer listening={false}>
            <Rect
              x={selectionRect.x}
              y={selectionRect.y}
              width={selectionRect.width}
              height={selectionRect.height}
              fill="rgba(99,153,255,0.08)"
              stroke="#6399ff"
              strokeWidth={1}
              dash={[5, 3]}
            />
          </Layer>
          {selectionRect.width > 10 &&
            selectionRect.height > 10 && (
              <Layer listening={false}>
                <Text
                  x={selectionRect.x + 4}
                  y={
                    selectionRect.y +
                    selectionRect.height +
                    5
                  }
                  text={`${Math.round(selectionRect.width)} × ${Math.round(selectionRect.height)}`}
                  fontSize={10}
                  fill="#6399ff"
                  fontFamily="monospace"
                />
              </Layer>
            )}
        </>
      )}
    </Stage>
  );
}
