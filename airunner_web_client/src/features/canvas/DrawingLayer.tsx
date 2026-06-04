import { useRef, useCallback, useEffect } from "react";
import { Line, Rect } from "react-konva";
import Konva from "konva";
import type { StrokeNode, ActiveTool } from "./useCanvasState";

interface DrawingLayerProps {
  strokes: StrokeNode[];
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  visible: boolean;
  opacity: number;
  onStrokeComplete: (stroke: Omit<StrokeNode, "id">) => void;
  isActive: boolean;
  canvasWidth: number;
  canvasHeight: number;
}

function getCanvasPos(e: Konva.KonvaEventObject<MouseEvent>) {
  const stage = e.currentTarget.getStage();
  if (!stage) return null;
  const raw = stage.getPointerPosition();
  if (!raw) return null;
  const t = stage.getAbsoluteTransform().copy().invert();
  return t.point(raw);
}

/** Clamp a point so the stroke cap stays within the document rectangle. */
function clampToDoc(
  x: number, y: number, w: number, h: number, inset: number,
): { x: number; y: number } {
  return {
    x: Math.max(inset, Math.min(w - inset, x)),
    y: Math.max(inset, Math.min(h - inset, y)),
  };
}

/** Linear interpolation between two points. */
function lerp(
  x1: number, y1: number, x2: number, y2: number, t: number,
): { x: number; y: number } {
  return { x: x1 + (x2 - x1) * t, y: y1 + (y2 - y1) * t };
}

const INTERP_THRESHOLD = 3; // px — max gap before inserting intermediate points

export default function DrawingLayer({
  strokes,
  activeTool,
  brushSize,
  brushColor,
  visible,
  opacity,
  onStrokeComplete,
  isActive,
  canvasWidth,
  canvasHeight,
}: DrawingLayerProps) {
  const isDrawing = useRef(false);
  const currentPoints = useRef<number[]>([]);
  const liveLineRef = useRef<Konva.Line>(null);

  const isDrawingTool = activeTool === "brush" || activeTool === "eraser";

  const handleMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (e.evt.button !== 0) return;
      if (!isActive || !isDrawingTool) return;
      const pos = getCanvasPos(e);
      if (!pos) return;
      const inset = brushSize / 2;
      const clamped = clampToDoc(pos.x, pos.y, canvasWidth, canvasHeight, inset);
      isDrawing.current = true;
      currentPoints.current = [clamped.x, clamped.y];
      if (liveLineRef.current) {
        liveLineRef.current.points([clamped.x, clamped.y]);
        liveLineRef.current.getLayer()?.batchDraw();
      }
    },
    [isActive, isDrawingTool, canvasWidth, canvasHeight, brushSize],
  );

  const handleMouseMove = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (!isDrawing.current) return;
      const pos = getCanvasPos(e);
      if (!pos) return;
      const inset = brushSize / 2;
      const clamped = clampToDoc(pos.x, pos.y, canvasWidth, canvasHeight, inset);
      const pts = currentPoints.current;
      if (pts.length >= 2) {
        const px = pts[pts.length - 2];
        const py = pts[pts.length - 1];
        const dx = clamped.x - px;
        const dy = clamped.y - py;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > INTERP_THRESHOLD) {
          // Insert intermediate points for smooth curves during fast strokes.
          const steps = Math.floor(dist / INTERP_THRESHOLD);
          for (let i = 1; i <= steps; i++) {
            const t = i / (steps + 1);
            const ip = lerp(px, py, clamped.x, clamped.y, t);
            pts.push(ip.x, ip.y);
          }
        }
      }
      pts.push(clamped.x, clamped.y);
      if (liveLineRef.current) {
        liveLineRef.current.points([...pts]);
        liveLineRef.current.getLayer()?.batchDraw();
      }
    },
    [canvasWidth, canvasHeight, brushSize],
  );

  const handleMouseUp = useCallback(() => {
    if (!isDrawing.current) return;
    isDrawing.current = false;
    if (liveLineRef.current) {
      liveLineRef.current.points([]);
      liveLineRef.current.getLayer()?.batchDraw();
    }
    if (currentPoints.current.length < 4) {
      currentPoints.current = [];
      return;
    }
    onStrokeComplete({
      points: [...currentPoints.current],
      color: activeTool === "eraser" ? "#000000" : brushColor,
      strokeWidth: brushSize,
      tool: activeTool as "brush" | "eraser",
    });
    currentPoints.current = [];
  }, [activeTool, brushSize, brushColor, onStrokeComplete]);

  // Catch mouseup anywhere in the browser window — Konva only fires
  // onMouseUp when the cursor is over the Stage/Canvas at release time.
  useEffect(() => {
    window.addEventListener("mouseup", handleMouseUp);
    return () => window.removeEventListener("mouseup", handleMouseUp);
  }, [handleMouseUp]);

  return (
    <>
      {strokes.map((stroke) => (
        <Line
          key={stroke.id}
          points={stroke.points}
          stroke={stroke.tool === "eraser" ? "#000000" : stroke.color}
          strokeWidth={stroke.strokeWidth}
          lineCap="round"
          lineJoin="round"
          globalCompositeOperation={stroke.tool === "eraser" ? "destination-out" : "source-over"}
          opacity={opacity}
          visible={visible}
        />
      ))}

      {/* Live preview line — updated imperatively */}
      <Line
        ref={liveLineRef}
        points={[]}
        stroke={activeTool === "eraser" ? "#000000" : brushColor}
        strokeWidth={brushSize}
        lineCap="round"
        lineJoin="round"
        globalCompositeOperation={activeTool === "eraser" ? "destination-out" : "source-over"}
        opacity={opacity}
        visible={visible && isDrawingTool}
        listening={false}
      />

      {/* Hit area — large enough in document coords to cover the zoomed/panned
          viewport, so strokes aren't interrupted when straying outside the doc. */}
      {isActive && isDrawingTool && (
        <Rect
          x={-50000}
          y={-50000}
          width={100000}
          height={100000}
          fill="transparent"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        />
      )}
    </>
  );
}
