// ── Canvas Stage ────────────────────────────────────────────────────────────
// Orchestrates zoom, keyboard, drawing overlay hooks, and per-tool hooks.
// All tool-specific interaction logic lives in stage/tools/<tool>/.
// Rendering is fully delegated to StageContent.
//
// To add a new tool:
//   1. Create stage/tools/<tool>/use<Tool>Tool.ts  (interaction hook)
//   2. Create stage/tools/<tool>/<Tool>Layer.tsx   (Konva rendering)
//   3. Call the hook here and wire onMouseDown/Move/Up into the chain below
//   4. Pass renderState to StageContent → render <ToolLayer> there
//   See client/src/features/canvas/CANVAS_TOOL_PATTERN.md for full details.

import { useRef, useCallback, useEffect, forwardRef } from "react";
import Konva from "konva";
import type { CanvasStageHandle } from "./stage/types";
import { zoom as zoomHook } from "./stage/zoom";
import { keyboard as keyboardHook } from "./stage/keyboard";
import { drawingOverlay as drawingOverlayHook } from "./stage/drawingOverlay";
import StageContent from "./stage/StageContent";
import PixelRuler from "./stage/PixelRuler";
import type { CanvasStageProps } from "./stage/types";
import { getCursor } from "./cursorUtils";
import { getCanvasPosFromStage } from "./stage/drawingHelpers";
import { moveTool } from "./stage/moveTool";
import { useLassoTool } from "./stage/tools/lasso/useLassoTool";
import { useSelectTool } from "./stage/tools/select/useSelectTool";
import { useWandTool } from "./stage/tools/wand/useWandTool";
import { useCropTool } from "./stage/tools/crop/useCropTool";
import { useBucketTool } from "./stage/tools/bucket/useBucketTool";
import { useSmudgeTool } from "./stage/tools/smudge/useSmudgeTool";
import { usePipetteTool } from "./stage/tools/pipette/usePipetteTool";
import { useZoomTool } from "./stage/tools/zoom/useZoomTool";
import { useTextTool } from "./stage/tools/text/useTextTool";
import { useCanvasContext } from "./CanvasContext";

export type { CanvasStageHandle } from "./stage/types";

const CanvasStage = forwardRef<CanvasStageHandle, CanvasStageProps>(
  function CanvasStage(props, ref) {
    const {
      documentWidth, documentHeight, documentBgColor,
      layers, layerGroups, displayOrder, activeLayerId,
      activeTool, moveMode, selectedLayerIds,
      brushSize, brushColor, maskStrokes,
      showGrid, snapToGrid,
      onAddStroke, onMoveImage, onMoveLayer,
      onAddMaskStroke, onAddLayerMaskStroke,
      onUndo, onRedo, setActiveTool, setActiveLayer,
      onZoomChange, isFitToView, isCenterView,
      onFitToViewChange, onCenterViewChange,
      gridLayerRef, maskLayerRef, stageRef, ghostLayerRef,
      sendLiveStroke, sendStrokeEnd,
    } = props;

    // ── Zoom + resize ──────────────────────────────────────────────────
    const containerRef = useRef<HTMLDivElement>(null);
    const { zoom, setZoom, stageSize, handleWheel } = zoomHook({
      stageRef, containerRef,
      documentWidth, documentHeight,
      onZoomChange, isFitToView, isCenterView,
      onFitToViewChange, onCenterViewChange,
      handleRef: ref,
    });

    // ── Drawing overlay ────────────────────────────────────────────────
    const drawing = drawingOverlayHook({
      stageRef, layers, activeLayerId, activeTool,
      brushSize, brushColor, documentWidth, documentHeight,
      onAddStroke, sendLiveStroke, sendStrokeEnd,
    });

    // ── Keyboard shortcuts ─────────────────────────────────────────────
    keyboardHook({ onUndo, onRedo, setActiveTool });

    // ── Move tool ──────────────────────────────────────────────────────
    const isMoveActive = activeTool === "move";
    const moveToolHandlers = moveTool({
      stageRef, moveMode, selectedLayerIds, layers, snapToGrid,
      onMoveLayer, onSetActiveLayer: setActiveLayer,
    });

    // ── Middle-mouse panning ───────────────────────────────────────────
    const isPanning       = useRef(false);
    const lastPointerPos  = useRef({ x: 0, y: 0 });
    const isCenterViewRef = useRef(isCenterView);
    const onCenterViewChangeRef = useRef(onCenterViewChange);
    useEffect(() => { isCenterViewRef.current = isCenterView; },        [isCenterView]);
    useEffect(() => { onCenterViewChangeRef.current = onCenterViewChange; }, [onCenterViewChange]);

    // ── Canvas-space position helper ───────────────────────────────────
    const getCanvasPos = useCallback(
      () => getCanvasPosFromStage(stageRef.current),
      [stageRef],
    );

    // ── Per-tool hooks ─────────────────────────────────────────────────
    // Each hook manages its own state, global-up listener, and key handlers.
    // onMouseDown/Move/Up return true when they consume the event.
    const lasso  = useLassoTool({
      isActive: activeTool === "lasso",
      getCanvasPos,
      stageRef,
    });

    const select = useSelectTool({
      isActive: activeTool === "select",
      getCanvasPos,
    });

    // Wand tool reads settings from canvas context
    const wandCtx = useCanvasContext();
    const wandSettingsRef = useRef({
      antialiasing: wandCtx.wandAntialiasing,
      featherEdges: wandCtx.wandFeatherEdges,
      featherRadius: wandCtx.wandFeatherRadius,
      selectTransparentAreas: wandCtx.wandSelectTransparentAreas,
      sampleMerged: wandCtx.wandSampleMerged,
      diagonalNeighbors: wandCtx.wandDiagonalNeighbors,
      threshold: wandCtx.wandThreshold,
    });
    wandSettingsRef.current = {
      antialiasing: wandCtx.wandAntialiasing,
      featherEdges: wandCtx.wandFeatherEdges,
      featherRadius: wandCtx.wandFeatherRadius,
      selectTransparentAreas: wandCtx.wandSelectTransparentAreas,
      sampleMerged: wandCtx.wandSampleMerged,
      diagonalNeighbors: wandCtx.wandDiagonalNeighbors,
      threshold: wandCtx.wandThreshold,
    };

    const wand = useWandTool({
      isActive: activeTool === "wand",
      getCanvasPos,
      stageRef,
      settingsRef: wandSettingsRef,
    });

    const crop = useCropTool({
      isActive: activeTool === "crop",
      getCanvasPos,
      stageRef,
    });

    // Bucket tool reads settings from canvas context
    const bucketSettingsRef = useRef({
      colorSource: wandCtx.bucketColorSource as "foreground" | "background",
      fillTransparentAreas: wandCtx.bucketFillTransparentAreas,
      antialiasing: wandCtx.bucketAntialiasing,
      threshold: wandCtx.bucketThreshold,
    });
    bucketSettingsRef.current = {
      colorSource: wandCtx.bucketColorSource as "foreground" | "background",
      fillTransparentAreas: wandCtx.bucketFillTransparentAreas,
      antialiasing: wandCtx.bucketAntialiasing,
      threshold: wandCtx.bucketThreshold,
    };

    const bucket = useBucketTool({
      isActive: activeTool === "bucket",
      getCanvasPos,
      stageRef,
      settingsRef: bucketSettingsRef,
      foregroundColor: wandCtx.brushColor,
      backgroundColor: wandCtx.documentBgColor,
    });

    const smudge = useSmudgeTool({
      isActive: activeTool === "smudge",
      getCanvasPos,
      stageRef,
      brushSize: wandCtx.smudgeSize,
    });

    const pipette = usePipetteTool({
      isActive: activeTool === "pipette",
      stageRef,
      pipetteTarget: wandCtx.pipetteTarget,
      onSetForegroundColor: wandCtx.setBrushColor,
      onSetBackgroundColor: wandCtx.setDocumentBgColor,
    });

    const zoomTool = useZoomTool({
      isActive: activeTool === "zoom",
      getCanvasPos,
      stageRef,
      zoomDirection: wandCtx.zoomDirection,
      onZoomApplied: useCallback(
        (scale: number) => {
          setZoom(scale);
          onZoomChange(scale);
          onFitToViewChange(false);
        },
        [setZoom, onZoomChange, onFitToViewChange],
      ),
    });

    const textTool = useTextTool({
      isActive: activeTool === "text",
      getCanvasPos,
      stageRef,
      textFont: wandCtx.textFont,
      textSize: wandCtx.textSize,
      textColor: wandCtx.textColor,
      layers: wandCtx.layers,
      addLayer: wandCtx.addLayer,
      renameLayer: wandCtx.renameLayer,
      deleteLayer: wandCtx.deleteLayer,
      setTextNode: wandCtx.setTextNode,
    });

    // ── Unified mouse handlers ─────────────────────────────────────────

    const handleMouseDown = useCallback(
      (e: Konva.KonvaEventObject<MouseEvent>) => {
        // Middle-button panning (any tool)
        if (e.evt.button === 1) {
          e.evt.preventDefault();
          isPanning.current = true;
          const container = stageRef.current?.container();
          if (container) container.style.cursor = "grabbing";
          const pos = stageRef.current?.getPointerPosition();
          if (pos) lastPointerPos.current = { x: pos.x, y: pos.y };
          return;
        }
        // Tool chain — first match wins
        if (isMoveActive && e.evt.button === 0) {
          moveToolHandlers.handleMoveMouseDown(e);
          return;
        }
        if (lasso.onMouseDown(e))  return;
        if (select.onMouseDown(e)) return;
        if (wand.onMouseDown(e))   return;
        if (crop.onMouseDown(e))   return;
        if (bucket.onMouseDown(e)) return;
        if (smudge.onMouseDown(e)) return;
        if (pipette.onMouseDown(e)) return;
        if (zoomTool.onMouseDown(e)) return;
        if (textTool.onMouseDown(e)) return;
      },
      [stageRef, isMoveActive, moveToolHandlers, lasso, select, wand, crop, bucket, smudge, pipette, zoomTool, textTool],
    );

    const handleMouseMove = useCallback(
      (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (isPanning.current) {
          const stage = stageRef.current;
          if (!stage) return;
          const pos = stage.getPointerPosition();
          if (!pos) return;
          const dx = pos.x - lastPointerPos.current.x;
          const dy = pos.y - lastPointerPos.current.y;
          stage.position({ x: stage.x() + dx, y: stage.y() + dy });
          if (isCenterViewRef.current) onCenterViewChangeRef.current(false);
          lastPointerPos.current = { x: pos.x, y: pos.y };
          return;
        }
        if (isMoveActive) { moveToolHandlers.handleMoveMouseMove(e); return; }
        if (lasso.onMouseMove(e))  return;
        if (wand.onMouseMove(e))   return;
        if (crop.onMouseMove(e))   return;
        if (bucket.onMouseMove(e)) return;
        if (smudge.onMouseMove(e)) return;
        if (pipette.onMouseMove(e)) return;
        if (zoomTool.onMouseMove(e)) return;
        if (textTool.onMouseMove(e)) return;
        select.onMouseMove(e);
      },
      [stageRef, isMoveActive, moveToolHandlers, lasso, select, wand, crop, bucket, smudge, pipette, zoomTool, textTool],
    );

    const handleMouseUp = useCallback(
      (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (isPanning.current) {
          isPanning.current = false;
          const container = stageRef.current?.container();
          if (container)
            container.style.cursor = getCursor(activeTool, layers.length > 0);
        }
        if (isMoveActive) { moveToolHandlers.handleMoveMouseUp(e); return; }
        if (lasso.onMouseUp(e))  return;
        if (wand.onMouseUp(e))   return;
        if (crop.onMouseUp(e))   return;
        if (bucket.onMouseUp(e)) return;
        if (smudge.onMouseUp(e)) return;
        if (pipette.onMouseUp(e)) return;
        if (zoomTool.onMouseUp(e)) return;
        if (textTool.onMouseUp(e)) return;
        select.onMouseUp(e);
      },
      [stageRef, activeTool, layers.length, isMoveActive, moveToolHandlers, lasso, select, wand, crop, bucket, smudge, pipette, zoomTool, textTool],
    );

    // Global up: only panning needs a CanvasStage-level handler now; each
    // tool hook manages its own global listener internally.
    useEffect(() => {
      const onGlobalUp = () => {
        if (!isPanning.current) return;
        isPanning.current = false;
        const container = stageRef.current?.container();
        if (container)
          container.style.cursor = getCursor(activeTool, layers.length > 0);
      };
      window.addEventListener("pointerup", onGlobalUp);
      window.addEventListener("mouseup",   onGlobalUp);
      return () => {
        window.removeEventListener("pointerup", onGlobalUp);
        window.removeEventListener("mouseup",   onGlobalUp);
      };
    }, [stageRef, activeTool, layers.length]);

    // ── Render ─────────────────────────────────────────────────────────

    return (
      <div
        ref={containerRef}
        style={{ width: "100%", height: "100%", background: "#1e1e2e", overflow: "hidden", position: "relative" }}
      >
        <StageContent
          stageRef={stageRef}
          gridLayerRef={gridLayerRef}
          maskLayerRef={maskLayerRef}
          ghostLayerRef={ghostLayerRef}
          stageSize={stageSize}
          zoom={zoom}
          documentWidth={documentWidth}
          documentHeight={documentHeight}
          documentBgColor={documentBgColor}
          layers={layers}
          layerGroups={layerGroups}
          displayOrder={displayOrder}
          activeLayerId={activeLayerId}
          activeTool={activeTool}
          moveMode={moveMode}
          brushSize={brushSize}
          brushColor={brushColor}
          maskStrokes={maskStrokes}
          showGrid={showGrid}
          snapToGrid={snapToGrid}
          // Tool render states
          lassoRenderState={lasso.renderState}
          selectRenderState={select.renderState}
          wandRenderState={wand.renderState}
          cropRenderState={crop.renderState}
          cropOnRectChange={crop.onCropRectChange}
          bucketRenderState={bucket.renderState}
          smudgeRenderState={smudge.renderState}
          pipetteRenderState={pipette.renderState}
          zoomToolRenderState={zoomTool.renderState}
          textToolRenderState={textTool.renderState}
          // Drawing overlay
          showBrushIndicator={drawing.showBrushIndicator}
          brushRadius={drawing.brushRadius}
          indicatorColor={drawing.indicatorColor}
          brushRingRef={drawing.brushRingRef}
          brushDotRef={drawing.brushDotRef}
          brushIndicatorLayerRef={drawing.brushIndicatorLayerRef}
          isDrawingTool={drawing.isDrawingTool}
          drawingOffsetX={drawing.drawingOffsetX}
          drawingOffsetY={drawing.drawingOffsetY}
          // Handlers
          handleWheel={handleWheel}
          handleMouseDown={handleMouseDown}
          handleMouseMove={handleMouseMove}
          handleMouseUp={handleMouseUp}
          handleOverlayPointerDown={drawing.handleOverlayPointerDown}
          handleOverlayPointerMove={drawing.handleOverlayPointerMove}
          handleOverlayPointerUp={drawing.handleOverlayPointerUp}
          updateBrushIndicator={drawing.updateBrushIndicator}
          onAddStroke={onAddStroke}
          onMoveImage={onMoveImage}
          onMoveLayer={onMoveLayer}
          onAddMaskStroke={onAddMaskStroke}
          onAddLayerMaskStroke={onAddLayerMaskStroke}
        />
        <PixelRuler
          stageRef={stageRef}
          stageSize={stageSize}
        />
      </div>
    );
  },
);

export default CanvasStage;
