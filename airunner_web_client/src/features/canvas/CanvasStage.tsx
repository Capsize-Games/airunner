import { useRef, useCallback, useEffect, useState, forwardRef, useImperativeHandle, useLayoutEffect } from "react";
import { Stage, Layer, Rect, Shape, Text } from "react-konva";
import Konva from "konva";
import CanvasLayerRenderer from "./CanvasLayer";
import ActiveGridArea from "./ActiveGridArea";
import MaskLayer from "./MaskLayer";
import type { CanvasLayer, ActiveGridArea as ActiveGridAreaType, StrokeNode, ActiveTool } from "./useCanvasState";

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
const CHECKER_SIZE = 8;

function makeBrushCursor(brushSize: number, zoom: number, color: string): string {
  const r = Math.max(4, Math.round((brushSize * zoom) / 2));
  const size = r * 2 + 8;
  const c = r + 4;
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${size}' height='${size}'>
    <circle cx='${c}' cy='${c}' r='${r}' fill='none' stroke='rgba(0,0,0,0.6)' stroke-width='2.5'/>
    <circle cx='${c}' cy='${c}' r='${r}' fill='none' stroke='${color}' stroke-width='1.5'/>
    <circle cx='${c}' cy='${c}' r='1.5' fill='${color}'/>
  </svg>`;
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}") ${c} ${c}, crosshair`;
}

function getCursor(tool: ActiveTool, brushSize: number, zoom: number, color: string): string {
  switch (tool) {
    case "select": return "crosshair";
    case "move":   return "grab";
    case "brush":  return makeBrushCursor(brushSize, zoom, color);
    case "eraser": return makeBrushCursor(brushSize, zoom, "rgba(200,200,200,0.9)");
    case "mask":   return makeBrushCursor(brushSize, zoom, "rgba(255,255,255,0.9)");
  }
}

const CanvasStage = forwardRef<CanvasStageHandle, CanvasStageProps>(function CanvasStage({
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
  const [selectionRect, setSelectionRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
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

  // ── Imperative handle ─────────────────────────────────────────────────────

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
        x: container ? (container.clientWidth  - documentWidth)  / 2 : 0,
        y: container ? (container.clientHeight - documentHeight) / 2 : 0,
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

  // ── Cursor ────────────────────────────────────────────────────────────────

  useEffect(() => {
    const container = stageRef.current?.container();
    if (container) {
      container.style.cursor = getCursor(activeTool, brushSize, zoom, brushColor);
    }
  }, [activeTool, brushSize, zoom, brushColor, stageRef]);

  // ── Zoom and pan ──────────────────────────────────────────────────────────

  const handleWheel = useCallback(
    (e: Konva.KonvaEventObject<WheelEvent>) => {
      e.evt.preventDefault();
      const stage = stageRef.current;
      if (!stage) return;
      const scaleBy = 1.08;
      const oldScale = stage.scaleX();
      const pointer = stage.getPointerPosition();
      if (!pointer) return;
      const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy;
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

  const getCanvasPos = useCallback((_e: Konva.KonvaEventObject<MouseEvent>) => {
    const stage = stageRef.current;
    if (!stage) return null;
    const raw = stage.getPointerPosition();
    if (!raw) return null;
    return stage.getAbsoluteTransform().copy().invert().point(raw);
  }, [stageRef]);

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
          setSelectionRect({ x: pos.x, y: pos.y, width: 0, height: 0 });
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
        stage.position({ x: stage.x() + dx, y: stage.y() + dy });
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
      if (container) container.style.cursor = getCursor(activeTool, brushSize, zoom, brushColor);
    }
    if (activeTool === "select") {
      selectionStartRef.current = null;
    }
  }, [stageRef, activeTool, brushSize, zoom, brushColor]);

  // ── Keyboard shortcuts ────────────────────────────────────────────────────

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault(); onUndo(); return;
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || (e.key === "z" && e.shiftKey))) {
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

  // ── Grid sceneFunc ────────────────────────────────────────────────────────

  const gridSceneFunc = useCallback(
    (ctx: Konva.Context) => {
      const native = (ctx as unknown as { _context: CanvasRenderingContext2D })._context;
      native.beginPath();
      native.strokeStyle = "rgba(255,255,255,0.09)";
      native.lineWidth = 0.5;
      for (let x = 0; x <= documentWidth; x += GRID_SIZE) {
        native.moveTo(x, 0); native.lineTo(x, documentHeight);
      }
      for (let y = 0; y <= documentHeight; y += GRID_SIZE) {
        native.moveTo(0, y); native.lineTo(documentWidth, y);
      }
      native.stroke();
    },
    [documentWidth, documentHeight],
  );

  // ── Checkerboard background sceneFunc ─────────────────────────────────────

  const checkerSceneFunc = useCallback(
    (ctx: Konva.Context) => {
      const native = (ctx as unknown as { _context: CanvasRenderingContext2D })._context;
      const cols = Math.ceil(documentWidth / CHECKER_SIZE);
      const rows = Math.ceil(documentHeight / CHECKER_SIZE);
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          native.fillStyle = (row + col) % 2 === 0 ? "#2a2a3a" : "#242432";
          native.fillRect(col * CHECKER_SIZE, row * CHECKER_SIZE, CHECKER_SIZE, CHECKER_SIZE);
        }
      }
    },
    [documentWidth, documentHeight],
  );

  const isTransparentBg = documentBgColor === "transparent";

  return (
    <div ref={containerRef} style={{ width: "100%", height: "100%", background: "#1e1e2e", overflow: "hidden" }}>
      <Stage
        width={stageSize.width}
        height={stageSize.height}
        ref={stageRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        style={{ display: "block" }}
      >
        {/* Document background */}
        <Layer listening={false}>
          {isTransparentBg ? (
            <Shape sceneFunc={checkerSceneFunc} />
          ) : (
            <Rect x={0} y={0} width={documentWidth} height={documentHeight} fill={documentBgColor} />
          )}
          {/* Document border */}
          <Rect
            x={0}
            y={0}
            width={documentWidth}
            height={documentHeight}
            fill="transparent"
            stroke="rgba(255,255,255,0.15)"
            strokeWidth={1}
            listening={false}
          />
        </Layer>

        {/* Content layers */}
        {layers.map((layer) => (
          <CanvasLayerRenderer
            key={layer.id}
            layer={layer}
            isActive={layer.id === activeLayerId}
            activeTool={activeTool}
            brushSize={brushSize}
            brushColor={brushColor}
            snapToGrid={snapToGrid}
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

        {/* Mask layer — shown when mask tool active, or eraser active with existing strokes */}
        {(activeTool === "mask" || (activeTool === "eraser" && maskStrokes.length > 0)) && (
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
            {/* Marching-ants effect via two overlapping dashed lines offset in time would need animation;
                for now a static dashed rect is sufficient */}
          </Layer>
        )}

        {/* Selection size label */}
        {selectionRect && selectionRect.width > 10 && selectionRect.height > 10 && activeTool === "select" && (
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
});

export default CanvasStage;
