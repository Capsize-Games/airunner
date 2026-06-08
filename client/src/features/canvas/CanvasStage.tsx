import {
  useRef, useCallback, useEffect, useState, forwardRef,
  useImperativeHandle, useLayoutEffect, useMemo,
} from "react";
import { Stage, Layer, Rect, Shape, Text, Circle, Line } from "react-konva";
import Konva from "konva";
import CanvasLayerRenderer from "./CanvasLayer";
import ActiveGridArea from "./ActiveGridArea";
import MaskLayer from "./MaskLayer";
import type {
  CanvasLayer, ActiveGridArea as ActiveGridAreaType,
  StrokeNode, ActiveTool, LayerGroup,
} from "./useCanvasState";
import { getCursor } from "./cursorUtils";
import CanvasBackground from "./CanvasBackground";

// ── Drawing helpers (shared with DrawingLayer) ─────────────────────────
const INTERP_THRESHOLD = 3;

function lerp(
  x1: number, y1: number, x2: number, y2: number, t: number,
): { x: number; y: number } {
  return { x: x1 + (x2 - x1) * t, y: y1 + (y2 - y1) * t };
}

function clampToDoc(
  x: number, y: number, w: number, h: number,
  inset: number, offsetX = 0, offsetY = 0,
): { x: number; y: number } {
  return {
    x: Math.max(inset - offsetX, Math.min(w - inset - offsetX, x)),
    y: Math.max(inset - offsetY, Math.min(h - inset - offsetY, y)),
  };
}

function getCanvasPosFromStage(stage: Konva.Stage | null) {
  if (!stage) return null;
  const raw = stage.getPointerPosition();
  if (!raw) return null;
  const t = stage.getAbsoluteTransform().copy().invert();
  return t.point(raw);
}

export interface CanvasStageHandle {
  zoomIn: () => void;
  zoomOut: () => void;
  zoomReset: () => void;
  centerView: () => void;
  fitView: () => void;
  getZoom: () => number;
  getStage: () => Konva.Stage | null;
}

interface CanvasStageProps {
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  displayOrder: string[];
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
  onAddLayerMaskStroke: (layerId: string, stroke: Omit<StrokeNode, "id">) => void;
  setActiveGridArea: (area: ActiveGridAreaType) => void;
  onUndo: () => void;
  onRedo: () => void;
  setActiveTool: (tool: ActiveTool) => void;
  onZoomChange: (zoom: number) => void;
  zoomMode: "fit" | "locked";
  onZoomModeChange: (mode: "fit" | "locked") => void;
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
    layerGroups,
    displayOrder,
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
    onAddLayerMaskStroke,
    setActiveGridArea,
    onUndo,
    onRedo,
    setActiveTool,
    onZoomChange,
    zoomMode,
    onZoomModeChange,
    gridLayerRef,
    maskLayerRef,
    stageRef,
  }, ref) {
    const isPanning = useRef(false);
    const lastPointerPos = useRef({ x: 0, y: 0 });
    const lastTouchDist = useRef(0);
    const [zoom, setZoom] = useState(1);
    const containerRef = useRef<HTMLDivElement>(null);
    const zoomModeRef = useRef(zoomMode);
    const onZoomModeChangeRef = useRef(onZoomModeChange);
    useEffect(() => { zoomModeRef.current = zoomMode; }, [zoomMode]);
    useEffect(() => { onZoomModeChangeRef.current = onZoomModeChange; }, [onZoomModeChange]);
    const selectionStartRef = useRef<{ x: number; y: number } | null>(null);
    const [selectionRect, setSelectionRect] = useState<{
      x: number; y: number; width: number; height: number;
    } | null>(null);
    const [stageSize, setStageSize] = useState({ width: 800, height: 600 });

    // ── Drawing overlay state (topmost layer for brush/eraser) ────────
    const isDrawingOverlay = useRef(false);
    const drawingPoints = useRef<number[]>([]);
    // The live-preview Line lives inside the active CanvasLayer's offset
    // <Group> (rendered by DrawingLayer) so it follows layer translations.
    // Access it through a global ref set by DrawingLayer's ref callback.
    const getLiveStroke = (): Konva.Line | null =>
      (window as unknown as Record<string, Konva.Line | undefined>)
        .__airunnerLiveStrokeRef ?? null;

    // Derive ordered layer list from displayOrder so the canvas always
    // respects the same stacking order as the layers sidebar.
    const orderedLayers = useMemo(() => {
      const result: CanvasLayer[] = [];
      const seen = new Set<string>();
      // First pass: follow displayOrder (group IDs → children; layer IDs → layer)
      for (const id of displayOrder) {
        const group = layerGroups.find((g) => g.id === id);
        if (group) {
          const children = layers.filter((l) => l.parentGroupId === id);
          for (const child of children) {
            if (!seen.has(child.id)) { result.push(child); seen.add(child.id); }
          }
          continue;
        }
        const layer = layers.find((l) => l.id === id);
        if (layer && !seen.has(layer.id)) {
          result.push(layer);
          seen.add(layer.id);
        }
      }
      // Second pass: catch any layers not referenced in displayOrder
      for (const layer of layers) {
        if (!seen.has(layer.id)) { result.push(layer); seen.add(layer.id); }
      }
      return result;
    }, [displayOrder, layerGroups, layers]);

    // Fill stage to container and zoom-to-fit on first mount
    useLayoutEffect(() => {
      const container = containerRef.current;
      if (!container) return;
      const PADDING = 40;
      const observer = new ResizeObserver(([entry]) => {
        const { width, height } = entry.contentRect;
        setStageSize({ width, height });
        const stage = stageRef.current;
        if (!stage) return;
        if (zoomModeRef.current === "fit") {
          const fitScale = Math.min(
            (width - PADDING) / Math.max(documentWidth, 1),
            (height - PADDING) / Math.max(documentHeight, 1),
            1,
          );
          stage.scale({ x: fitScale, y: fitScale });
          setZoom(fitScale);
          onZoomChange(fitScale);
          stage.position({
            x: (width - documentWidth * fitScale) / 2,
            y: (height - documentHeight * fitScale) / 2,
          });
        }
      });
      observer.observe(container);
      return () => observer.disconnect();
    }, [stageRef, documentWidth, documentHeight, onZoomChange]);

    // ── Imperative handle ─────────────────────────────────────────────

    useImperativeHandle(ref, () => ({
      zoomIn: () => {
        const stage = stageRef.current;
        if (!stage) return;
        const newScale = Math.min(stage.scaleX() * 1.25, 20);
        stage.scale({ x: newScale, y: newScale });
        setZoom(newScale);
        onZoomChange(newScale);
        onZoomModeChange("locked");
      },
      zoomOut: () => {
        const stage = stageRef.current;
        if (!stage) return;
        const newScale = Math.max(stage.scaleX() / 1.25, 0.05);
        stage.scale({ x: newScale, y: newScale });
        setZoom(newScale);
        onZoomChange(newScale);
        onZoomModeChange("locked");
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
        onZoomModeChange("locked");
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
      fitView: () => {
        const stage = stageRef.current;
        const container = containerRef.current;
        if (!stage || !container) return;
        const PADDING = 40;
        const width = container.clientWidth;
        const height = container.clientHeight;
        const fitScale = Math.min(
          (width - PADDING) / Math.max(documentWidth, 1),
          (height - PADDING) / Math.max(documentHeight, 1),
          1,
        );
        stage.scale({ x: fitScale, y: fitScale });
        stage.position({
          x: (width - documentWidth * fitScale) / 2,
          y: (height - documentHeight * fitScale) / 2,
        });
        setZoom(fitScale);
        onZoomChange(fitScale);
        onZoomModeChange("fit");
      },
      getZoom: () => stageRef.current?.scaleX() ?? 1,
      getStage: () => stageRef.current,
    }), [stageRef, documentWidth, documentHeight, onZoomChange, onZoomModeChange]);

    // Multi-touch: two-finger drag to pan, pinch to zoom.
    useEffect(() => {
      const container = containerRef.current;
      if (!container) return;
      const onStart = (e: TouchEvent) => {
        if (e.touches.length < 2) return;
        e.preventDefault();
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        lastPointerPos.current = {
          x: (t1.clientX + t2.clientX) / 2,
          y: (t1.clientY + t2.clientY) / 2,
        };
        lastTouchDist.current = Math.hypot(
          t1.clientX - t2.clientX,
          t1.clientY - t2.clientY,
        );
      };
      const onMove = (e: TouchEvent) => {
        if (e.touches.length < 2) return;
        e.preventDefault();
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        const mx = (t1.clientX + t2.clientX) / 2;
        const my = (t1.clientY + t2.clientY) / 2;
        const dx = mx - lastPointerPos.current.x;
        const dy = my - lastPointerPos.current.y;
        lastPointerPos.current = { x: mx, y: my };
        const dist = Math.hypot(
          t1.clientX - t2.clientX,
          t1.clientY - t2.clientY,
        );
        const stage = stageRef.current;
        if (!stage) return;
        // Only zoom when distance changes by at least 3% — prevents
        // jittery zoom competing with pan when fingers move together.
        if (lastTouchDist.current > 0) {
          const pinchRatio = dist / lastTouchDist.current;
          if (Math.abs(pinchRatio - 1) > 0.03) {
            const newScale = Math.max(0.05, Math.min(
              stage.scaleX() * pinchRatio, 20,
            ));
            stage.scale({ x: newScale, y: newScale });
            setZoom(newScale);
            onZoomChange(newScale);
            onZoomModeChangeRef.current("locked");
            lastTouchDist.current = dist;
          }
        }
        stage.position({
          x: stage.x() + dx,
          y: stage.y() + dy,
        });
        lastTouchDist.current = dist;
      };
      const onEnd = () => { lastTouchDist.current = 0; };
      container.addEventListener("touchstart", onStart, { passive: false });
      container.addEventListener("touchmove", onMove, { passive: false });
      container.addEventListener("touchend", onEnd);
      return () => {
        container.removeEventListener("touchstart", onStart);
        container.removeEventListener("touchmove", onMove);
        container.removeEventListener("touchend", onEnd);
      };
    }, [stageRef, onZoomChange]);

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
        onZoomModeChangeRef.current("locked");
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
        const target = e.target as HTMLElement;
        const tag = target.tagName;
        if (
          tag === "INPUT" ||
          tag === "TEXTAREA" ||
          tag === "SELECT" ||
          target.isContentEditable
        ) {
          return;
        }
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
          native.lineTo(documentHeight, y);
        }
        native.stroke();
      },
      [documentWidth, documentHeight],
    );

    // ── Drawing overlay handlers (brush/eraser) ───────────────────────

    const activeLayer = useMemo(
      () => layers.find((l) => l.id === activeLayerId) ?? null,
      [layers, activeLayerId],
    );

    const isDrawingTool = activeTool === "brush" || activeTool === "eraser";
    const drawingOffsetX = activeLayer?.offsetX ?? 0;
    const drawingOffsetY = activeLayer?.offsetY ?? 0;

    const handleOverlayPointerDown = useCallback(
      (e: Konva.KonvaEventObject<PointerEvent>) => {
        if (e.evt.button !== 0) return;
        if (!activeLayerId || !isDrawingTool) return;
        const pos = getCanvasPosFromStage(stageRef.current);
        if (!pos) return;
        const local = { x: pos.x - drawingOffsetX, y: pos.y - drawingOffsetY };
        const clamped = clampToDoc(
          local.x, local.y, documentWidth, documentHeight,
          0, drawingOffsetX, drawingOffsetY,
        );
        isDrawingOverlay.current = true;
        drawingPoints.current = [clamped.x, clamped.y];
        if (getLiveStroke()) {
          getLiveStroke().points([clamped.x, clamped.y]);
          getLiveStroke().getLayer()?.batchDraw();
        }
      },
      [activeLayerId, isDrawingTool, brushSize, documentWidth, documentHeight,
       drawingOffsetX, drawingOffsetY],
    );

    const handleOverlayPointerMove = useCallback(
      (e: Konva.KonvaEventObject<PointerEvent>) => {
        if (!isDrawingOverlay.current) return;
        const pos = getCanvasPosFromStage(stageRef.current);
        if (!pos) return;
        const local = { x: pos.x - drawingOffsetX, y: pos.y - drawingOffsetY };
        const clamped = clampToDoc(
          local.x, local.y, documentWidth, documentHeight,
          0, drawingOffsetX, drawingOffsetY,
        );
        const pts = drawingPoints.current;
        if (pts.length >= 2) {
          const px = pts[pts.length - 2];
          const py = pts[pts.length - 1];
          const dx = clamped.x - px;
          const dy = clamped.y - py;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > INTERP_THRESHOLD) {
            const steps = Math.floor(dist / INTERP_THRESHOLD);
            for (let i = 1; i <= steps; i++) {
              const t = i / (steps + 1);
              const ip = lerp(px, py, clamped.x, clamped.y, t);
              pts.push(ip.x, ip.y);
            }
          }
        }
        pts.push(clamped.x, clamped.y);
        if (getLiveStroke()) {
          getLiveStroke().points([...pts]);
          getLiveStroke().getLayer()?.batchDraw();
        }
      },
      [brushSize, documentWidth, documentHeight, drawingOffsetX, drawingOffsetY],
    );

    const handleOverlayPointerUp = useCallback(() => {
      if (!isDrawingOverlay.current) return;
      isDrawingOverlay.current = false;
      if (getLiveStroke()) {
        getLiveStroke().points([]);
        getLiveStroke().getLayer()?.batchDraw();
      }
      if (drawingPoints.current.length < 4) {
        drawingPoints.current = [];
        return;
      }
      onAddStroke({
        points: [...drawingPoints.current],
        color: activeTool === "eraser" ? "#000000" : brushColor,
        strokeWidth: brushSize,
        tool: activeTool as "brush" | "eraser",
      });
      drawingPoints.current = [];
    }, [activeTool, brushSize, brushColor, onAddStroke]);

    // Catch pointerup anywhere in the browser window — Konva only fires
    // onPointerUp when the pointer is over the Stage/Canvas at release.
    useEffect(() => {
      window.addEventListener("pointerup", handleOverlayPointerUp);
      return () => window.removeEventListener("pointerup", handleOverlayPointerUp);
    }, [handleOverlayPointerUp]);

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

          {/* Content layers — rendered in displayOrder so canvas stacking
              always matches the layers sidebar */}
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
                    ? (stroke) => onAddLayerMaskStroke(layer.id, stroke)
                    : onAddStroke
                }
                onMoveImage={onMoveImage}
                onMoveLayer={onMoveLayer}
              />
            );
          })}

          {/* Drawing overlay — sits ABOVE all content layers so pointer
              events always reach the hit area, even when shapes in other
              layers are under the cursor.  Only interactive for brush/
              eraser tools. */}
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
              <Line
                points={[]}
                stroke={activeTool === "eraser" ? "#000000" : brushColor}
                strokeWidth={brushSize}
                lineCap="round"
                lineJoin="round"
                globalCompositeOperation={activeTool === "eraser" ? "destination-out" : "source-over"}
                listening={false}
              />
            </Layer>
          )}

          {/* Pixel grid */}
          <Layer listening={false} visible={showGrid}>
            <Shape sceneFunc={gridSceneFunc} />
          </Layer>

          {/* Active Grid Area — hidden; ref kept for compatibility */}
          <Layer ref={gridLayerRef} listening={false} visible={false} />

          {/* Mask layer — routes to per-layer mask when active layer has one */}
          {activeTool === "mask" && (() => {
            const activeLayer = layers.find((l) => l.id === activeLayerId);
            const hasLayerMask = Array.isArray(activeLayer?.maskStrokes);
            const handleMaskStroke = hasLayerMask && activeLayerId
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
