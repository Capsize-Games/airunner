import {
  useRef, useCallback, useEffect, useState, forwardRef,
  useImperativeHandle, useLayoutEffect,
} from "react";
import { Stage, Layer, Rect, Shape, Text, Circle } from "react-konva";
import Konva from "konva";
import CanvasLayerRenderer from "./CanvasLayer";
import ActiveGridArea from "./ActiveGridArea";
import MaskLayer from "./MaskLayer";
import type {
  CanvasLayer, ActiveGridArea as ActiveGridAreaType,
  StrokeNode, ActiveTool,
} from "./useCanvasState";
import { getCursor } from "./cursorUtils";
import CanvasBackground from "./CanvasBackground";

export interface CanvasStageHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  zoomReset: () => void;
  centerView: () => void;
  getZoom: () => number;
  getStage: () => Konva.Stage | null;
}

interface CanvasStageProps {
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  layers: CanvasLayer[];
  activeLayerId: string | null;
  activeGridArea: ActiveGridAreaType;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  maskStrokes: StrokeNode[];
  showGrid: boolean;
  snapToGrid: boolean;
  onAddStroke: (stroke: Omit<StrokeNode, "id">) => void;
  onMoveImage: (layerId: string, imageId: string, x: number, y: number) => void;
  onMoveLayer: (layerId: string, x: number, y: number) => void;
  onAddMaskStroke: (stroke: Omit<StrokeNode, "id">) => void;
  setActiveGridArea: (area: ActiveGridAreaType) => void;
  onUndo: () => void;
  onRedo: () => void;
  setActiveTool: (tool: ActiveTool) => void;
  onZoomChange: (zoom: number) => void;
  gridLayerRef: React.RefObject<Konva.Layer>;
  maskLayerRef: React.RefObject<Konva.Layer>;
  stageRef: React.RefObject<Konva.Stage>;
}

const GRID_SIZE = 16;

const CanvasStage = forwardRef<CanvasStageHandle, CanvasStageProps>(
  function CanvasStage({
    documentWidth,
    documentHeight,
    documentBgColor,
    layers,
    activeLayerId,
    activeGridArea,
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
    setActiveGridArea,
    onUndo,
    onRedo,
    setActiveTool,
    onZoomChange,
    gridLayerRef,
    maskLayerRef,
    stageRef,
  }, ref) {
    const isPanning = useRef(false);
    const lastPointerPos = useRef({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const containerRef = useRef<HTMLDivElement>(null);
    const selectionStartRef = useRef<{ x: number; y: number } | null>(null);
    const [selectionRect, setSelectionRect] = useState<{
      x: number; y: number; width: number; height: number;
    } | null>(null);
    const [stageSize, setStageSize] = useState({ width: 800, height: 600 });

    // Fill stage to container and center document on resize
    useLayoutEffect(() => {
      const container = containerRef.current;
      if (!container) return;
      const observer = new ResizeObserver(([entry]) => {
        const { width, height } = entry.contentRect;
        setStageSize({ width, height });
        const stage = stageRef.current;
        if (stage && stage.x() === 0 && stage.y() === 0) {
          stage.position({
            x: (width - documentWidth) / 2,
            y: (height - documentHeight) / 2,
          });
        }
      });
      observer.observe(container);
      return () => observer.disconnect();
    }, [stageRef, documentWidth, documentHeight]);

    // ── Imperative handle ─────────────────────────────────────────────

    useImperativeHandle(ref, () => ({
      zoomIn: () => {
        const stage = stageRef.current;
        if (!stage) return;
        const newScale = Math.min(stage.scaleX() * 1.25, 20);
        stage.scale({ x: newScale, y: newScale });
        setZoom(newScale);
        onZoomChange(newScale);
      },
      zoomOut: () => {
        const stage = stageRef.current;
        if (!stage) return;
        const newScale = Math.max(stage.scaleX() / 1.25, 0.05);
        stage.scale({ x: newScale, y: newScale });
        setZoom(newScale);
        onZoomChange(newScale);
      },
      zoomReset: () => {
        const stage = stageRef.current;
        const container = containerRef.current;
        if (!stage) return;
        stage.scale({ x: 1, y: 1 });
        stage.position({
          x: container
            ? (container.clientWidth  - documentWidth)  / 2
            : 0,
          y: container
            ? (container.clientHeight - documentHeight) / 2
            : 0,
        });
        setZoom(1);
        onZoomChange(1);
      },
      centerView: () => {
        const stage = stageRef.current;
        const container = containerRef.current;
        if (!stage || !container) return;
        const scale = stage.scaleX();
        stage.position({
          x: (container.clientWidth - documentWidth * scale) / 2,
          y: (container.clientHeight - documentHeight * scale) / 2,
        });
      },
      getZoom: () => stageRef.current?.scaleX() ?? 1,
      getStage: () => stageRef.current,
    }), [stageRef, documentWidth, documentHeight, onZoomChange]);

    // Clear selection when switching away from select tool
    useEffect(() => {
      if (activeTool !== "select") setSelectionRect(null);
    }, [activeTool]);

    // ── Cursor ────────────────────────────────────────────────────────

    // Update cursor when active tool or layer count changes.
    useEffect(() => {
      const container = stageRef.current?.container();
      if (container) {
        container.style.cursor = getCursor(activeTool, layers.length > 0);
      }
    }, [activeTool, layers.length, stageRef]);

    // Brush-size indicator circle (imperative Konva, no React re-renders).
    const brushRingRef = useRef<Konva.Circle | null>(null);
    const brushDotRef = useRef<Konva.Circle | null>(null);
    const brushIndicatorLayerRef = useRef<Konva.Layer | null>(null);
    const showBrushIndicator =
      activeTool === "brush" ||
      activeTool === "eraser" ||
      activeTool === "mask";
    const brushRadius = (brushSize * zoom) / 2;
    const indicatorColor = activeTool === "eraser"
      ? "rgba(200,200,200,0.8)"
      : activeTool === "mask"
        ? "rgba(255,255,255,0.8)"
        : brushColor;

    /** Update the brush indicator position and visibility imperatively. */
    const updateBrushIndicator = useCallback(
      (pos: { x: number; y: number } | null) => {
        const ring = brushRingRef.current;
        const dot = brushDotRef.current;
        if (!ring || !dot) return;
        if (pos) {
          ring.position(pos);
          dot.position(pos);
          ring.visible(true);
          dot.visible(true);
        } else {
          ring.visible(false);
          dot.visible(false);
        }
      },
      [],
    );

    // Use a native Konva mousemove listener for the brush indicator so it
    // updates synchronously with the canvas render cycle, not React's.
    useEffect(() => {
      const stage = stageRef.current;
      if (!stage) return;
      const handler = () => {
        const raw = stage.getPointerPosition();
        if (!raw) return;
        const doc = stage.getAbsoluteTransform().copy().invert().point(raw);
        updateBrushIndicator(doc);
      };
      stage.on("mousemove", handler);
      return () => { stage.off("mousemove", handler); };
    }, [updateBrushIndicator]);

    // ── Zoom and pan ──────────────────────────────────────────────────

    const handleWheel = useCallback(
      (e: Konva.KonvaEventObject<WheelEvent>) => {
        e.evt.preventDefault();
        const stage = stageRef.current;
        if (!stage) return;
        const scaleBy = 1.08;
        const oldScale = stage.scaleX();
        const pointer = stage.getPointerPosition();
        if (!pointer) return;
        const newScale =
          e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy;
        const clampedScale = Math.max(0.05, Math.min(newScale, 20));
        const mousePointTo = {
          x: (pointer.x - stage.x()) / oldScale,
          y: (pointer.y - stage.y()) / oldScale,
        };
        stage.scale({ x: clampedScale, y: clampedScale });
        stage.position({
          x: pointer.x - mousePointTo.x * clampedScale,
          y: pointer.y - mousePointTo.y * clampedScale,
        });
        setZoom(clampedScale);
        onZoomChange(clampedScale);
      },
      [stageRef, onZoomChange],
    );

    const getCanvasPos = useCallback(
      (_e: Konva.KonvaEventObject<MouseEvent>) => {
        const stage = stageRef.current;
        if (!stage) return null;
        const raw = stage.getPointerPosition();
        if (!raw) return null;
        return stage.getAbsoluteTransform().copy().invert().point(raw);
      },
      [stageRef],
    );

    const handleMouseDown = useCallback(
      (e: Konva.KonvaEventObject<MouseEvent>) => {
        if (e.evt.button === 1) {
          isPanning.current = true;
          const container = stageRef.current?.container();
          if (container) container.style.cursor = "grabbing";
          const pos = stageRef.current?.getPointerPosition();
          if (pos) lastPointerPos.current = { x: pos.x, y: pos.y };
          return;
        }
        if (activeTool === "select" && e.evt.button === 0) {
          const pos = getCanvasPos(e);
          if (pos) {
            selectionStartRef.current = pos;
            setSelectionRect({
              x: pos.x, y: pos.y, width: 0, height: 0,
            });
          }
        }
      },
      [stageRef, activeTool, getCanvasPos],
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
          stage.position({
            x: stage.x() + dx, y: stage.y() + dy,
          });
          lastPointerPos.current = { x: pos.x, y: pos.y };
          return;
        }
        if (activeTool === "select" && selectionStartRef.current) {
          const pos = getCanvasPos(e);
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
            activeTool, layers.length > 0,
          );
        }
      }
      if (activeTool === "select") {
        selectionStartRef.current = null;
      }
    }, [stageRef, activeTool, brushSize, zoom, brushColor, layers.length]);

    // ── Keyboard shortcuts ────────────────────────────────────────────

    useEffect(() => {
      const onKey = (e: KeyboardEvent) => {
        if (
          (e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey
        ) {
          e.preventDefault(); onUndo(); return;
        }
        if (
          (e.ctrlKey || e.metaKey) &&
          (e.key === "y" || (e.key === "z" && e.shiftKey))
        ) {
          e.preventDefault(); onRedo(); return;
        }
        if (e.key === "b" || e.key === "B") setActiveTool("brush");
        else if (e.key === "e" || e.key === "E") setActiveTool("eraser");
        else if (e.key === "m" || e.key === "M") setActiveTool("mask");
        else if (e.key === "v" || e.key === "V") setActiveTool("move");
        else if (e.key === "s" || e.key === "S") setActiveTool("select");
      };
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }, [onUndo, onRedo, setActiveTool]);

    // ── Grid sceneFunc ────────────────────────────────────────────────

    const gridSceneFunc = useCallback(
      (ctx: Konva.Context) => {
        const native = (
          ctx as unknown as { _context: CanvasRenderingContext2D }
        )._context;
        native.beginPath();
        native.strokeStyle = "rgba(255,255,255,0.09)";
        native.lineWidth = 0.5;
        for (let x = 0; x <= documentWidth; x += GRID_SIZE) {
          native.moveTo(x, 0);
          native.lineTo(x, documentHeight);
        }
        for (let y = 0; y <= documentHeight; y += GRID_SIZE) {
          native.moveTo(0, y);
          native.lineTo(documentWidth, y);
        }
        native.stroke();
      },
      [documentWidth, documentHeight],
    );

    return (
      <div
        ref={containerRef}
        style={{
          width: "100%", height: "100%",
          background: "#1e1e2e", overflow: "hidden",
        }}
      >
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
              const doc = stage.getAbsoluteTransform()
                .copy().invert().point(raw);
              updateBrushIndicator(doc);
            }
          }}
          style={{ display: "block" }}
        >
          {/* Document background */}
          <CanvasBackground
            documentWidth={documentWidth}
            documentHeight={documentHeight}
            documentBgColor={documentBgColor}
          />

          {/* Content layers */}
          {layers.map((layer, index) => (
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
              onStrokeComplete={onAddStroke}
              onMoveImage={onMoveImage}
              onMoveLayer={onMoveLayer}
            />
          ))}

          {/* Pixel grid */}
          <Layer listening={false} visible={showGrid}>
            <Shape sceneFunc={gridSceneFunc} />
          </Layer>

          {/* Active Grid Area — only listens when move/select tool active */}
          <Layer
            ref={gridLayerRef}
            listening={activeTool === "move" || activeTool === "select"}
          >
            <ActiveGridArea
              area={activeGridArea}
              documentWidth={documentWidth}
              documentHeight={documentHeight}
              onChange={setActiveGridArea}
              snapToGrid={snapToGrid}
            />
          </Layer>

          {/* Mask layer */}
          {(activeTool === "mask" ||
            (activeTool === "eraser" && maskStrokes.length > 0)) && (
            <Layer ref={maskLayerRef}>
              <MaskLayer
                strokes={maskStrokes}
                activeTool={activeTool}
                brushSize={brushSize}
                documentWidth={documentWidth}
                documentHeight={documentHeight}
                onStrokeComplete={onAddMaskStroke}
              />
            </Layer>
          )}

          {/* Brush-size indicator circle */}
          {showBrushIndicator && (
            <Layer listening={false} ref={brushIndicatorLayerRef}>
              <Circle
                ref={brushRingRef}
                radius={brushRadius}
                fill="transparent"
                stroke={indicatorColor}
                strokeWidth={2 / zoom}
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

          {/* Selection rectangle */}
          {selectionRect && activeTool === "select" && (
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
          )}

          {/* Selection size label */}
          {selectionRect &&
            selectionRect.width > 10 &&
            selectionRect.height > 10 &&
            activeTool === "select" && (
            <Layer listening={false}>
              <Text
                x={selectionRect.x + 4}
                y={selectionRect.y + selectionRect.height + 5}
                text={`${Math.round(selectionRect.width)} × ${Math.round(selectionRect.height)}`}
                fontSize={10}
                fill="#6399ff"
                fontFamily="monospace"
              />
            </Layer>
          )}
        </Stage>
      </div>
    );
  },
);

export default CanvasStage;
