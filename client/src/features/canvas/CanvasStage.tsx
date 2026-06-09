// ── Canvas Stage ────────────────────────────────────────────────────────
// Composer: orchestrates zoom, keyboard, drawing overlay hooks, and
// delegates rendering to CanvasStageContent.
//
// Exports:
//   CanvasStageHandle, CanvasStage (default), CanvasStageProps (from types)

import { useRef, useCallback, useState, forwardRef } from "react";
import Konva from "konva";
import type { CanvasStageHandle } from "./stage/types";
import { zoom as zoomHook } from "./stage/zoom";
import { keyboard as keyboardHook } from "./stage/keyboard";
import { drawingOverlay as drawingOverlayHook } from "./stage/drawingOverlay";
import StageContent from "./stage/StageContent";
import type { CanvasStageProps } from "./stage/types";
import { getCursor } from "./cursorUtils";
import { getCanvasPosFromStage } from "./stage/drawingHelpers";

export type { CanvasStageHandle } from "./stage/types";

const CanvasStage = forwardRef<
  CanvasStageHandle,
  CanvasStageProps
>(function CanvasStage(props, ref) {
  const {
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
    onAddStroke,
    onMoveImage,
    onMoveLayer,
    onAddMaskStroke,
    onAddLayerMaskStroke,
    onUndo,
    onRedo,
    setActiveTool,
    onZoomChange,
    zoomMode,
    onZoomModeChange,
    gridLayerRef,
    maskLayerRef,
    stageRef,
    ghostLayerRef,
    sendLiveStroke,
    sendStrokeEnd,
  } = props;

  // ── Zoom + resize ────────────────────────────────────────────────────
  const containerRef = useRef<HTMLDivElement>(null);
  const { zoom, stageSize, handleWheel } = zoomHook({
    stageRef,
    containerRef,
    documentWidth,
    documentHeight,
    onZoomChange,
    zoomMode,
    onZoomModeChange,
    handleRef: ref,
  });
  // ── Drawing overlay ──────────────────────────────────────────────────
  const drawing = drawingOverlayHook({
    stageRef,
    layers,
    activeLayerId,
    activeTool,
    brushSize,
    brushColor,
    documentWidth,
    documentHeight,
    zoom,
    onAddStroke,
    sendLiveStroke,
    sendStrokeEnd,
  });

  // ── Keyboard shortcuts ───────────────────────────────────────────────
  keyboardHook({ onUndo, onRedo, setActiveTool });

  // ── Mouse panning ────────────────────────────────────────────────────
  const isPanning = useRef(false);
  const lastPointerPos = useRef({ x: 0, y: 0 });

  // ── Selection rect ───────────────────────────────────────────────────
  const selectionStartRef = useRef<{
    x: number;
    y: number;
  } | null>(null);
  const [selectionRect, setSelectionRect] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>(null);

  const getCanvasPos = useCallback(
    () => getCanvasPosFromStage(stageRef.current),
    [stageRef],
  );

  const handleMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (e.evt.button === 1) {
        isPanning.current = true;
        const container = stageRef.current?.container();
        if (container) container.style.cursor = "grabbing";
        const pos = stageRef.current?.getPointerPosition();
        if (pos)
          lastPointerPos.current = {
            x: pos.x,
            y: pos.y,
          };
        return;
      }
      if (activeTool === "select" && e.evt.button === 0) {
        const pos = getCanvasPos();
        if (pos) {
          selectionStartRef.current = pos;
          setSelectionRect({
            x: pos.x,
            y: pos.y,
            width: 0,
            height: 0,
          });
        }
      }
    },
    [stageRef, activeTool, getCanvasPos],
  );

  const handleMouseMove = useCallback(
    () => {
      if (isPanning.current) {
        const stage = stageRef.current;
        if (!stage) return;
        const pos = stage.getPointerPosition();
        if (!pos) return;
        const dx = pos.x - lastPointerPos.current.x;
        const dy = pos.y - lastPointerPos.current.y;
        stage.position({
          x: stage.x() + dx,
          y: stage.y() + dy,
        });
        lastPointerPos.current = { x: pos.x, y: pos.y };
        return;
      }
      if (
        activeTool === "select" &&
        selectionStartRef.current
      ) {
        const pos = getCanvasPos();
        if (pos) {
          const sx = selectionStartRef.current.x;
          const sy = selectionStartRef.current.y;
          setSelectionRect({
            x: Math.min(sx, pos.x),
            y: Math.min(sy, pos.y),
            width: Math.abs(pos.x - sx),
            height: Math.abs(pos.y - sy),
          });
        }
      }
    },
    [stageRef, activeTool, getCanvasPos],
  );

  const handleMouseUp = useCallback(() => {
    if (isPanning.current) {
      isPanning.current = false;
      const container = stageRef.current?.container();
      if (container) {
        container.style.cursor = getCursor(
          activeTool,
          layers.length > 0,
        );
      }
    }
    if (activeTool === "select") {
      selectionStartRef.current = null;
    }
  }, [stageRef, activeTool, layers.length]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "100%",
        background: "#1e1e2e",
        overflow: "hidden",
      }}
    >
      <StageContent
        stageRef={stageRef}
        gridLayerRef={gridLayerRef}
        maskLayerRef={maskLayerRef}
        ghostLayerRef={ghostLayerRef}
        stageSize={stageSize}
        documentWidth={documentWidth}
        documentHeight={documentHeight}
        documentBgColor={documentBgColor}
        layers={layers}
        layerGroups={layerGroups}
        displayOrder={displayOrder}
        activeLayerId={activeLayerId}
        activeTool={activeTool}
        brushSize={brushSize}
        brushColor={brushColor}
        maskStrokes={maskStrokes}
        showGrid={showGrid}
        snapToGrid={snapToGrid}
        selectionRect={selectionRect}
        showBrushIndicator={drawing.showBrushIndicator}
        brushRadius={drawing.brushRadius}
        indicatorColor={drawing.indicatorColor}
        brushRingRef={drawing.brushRingRef}
        brushDotRef={drawing.brushDotRef}
        brushIndicatorLayerRef={
          drawing.brushIndicatorLayerRef
        }
        isDrawingTool={drawing.isDrawingTool}
        drawingOffsetX={drawing.drawingOffsetX}
        drawingOffsetY={drawing.drawingOffsetY}
        handleWheel={handleWheel}
        handleMouseDown={handleMouseDown}
        handleMouseMove={handleMouseMove}
        handleMouseUp={handleMouseUp}
        handleOverlayPointerDown={
          drawing.handleOverlayPointerDown
        }
        handleOverlayPointerMove={
          drawing.handleOverlayPointerMove
        }
        handleOverlayPointerUp={
          drawing.handleOverlayPointerUp
        }
        updateBrushIndicator={
          drawing.updateBrushIndicator
        }
        onAddStroke={onAddStroke}
        onMoveImage={onMoveImage}
        onMoveLayer={onMoveLayer}
        onAddMaskStroke={onAddMaskStroke}
        onAddLayerMaskStroke={onAddLayerMaskStroke}
      />
    </div>
  );
});

export default CanvasStage;
