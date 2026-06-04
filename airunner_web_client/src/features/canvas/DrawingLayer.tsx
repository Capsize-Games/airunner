import { useRef, useCallback } from "react";
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
}

function getCanvasPos(e: Konva.KonvaEventObject<MouseEvent>) {
  const stage = e.currentTarget.getStage();
  if (!stage) return null;
  const raw = stage.getPointerPosition();
  if (!raw) return null;
  const t = stage.getAbsoluteTransform().copy().invert();
  return t.point(raw);
}

export default function DrawingLayer({
  strokes,
  activeTool,
  brushSize,
  brushColor,
  visible,
  opacity,
  onStrokeComplete,
  isActive,
}: DrawingLayerProps) {
  const isDrawing = useRef(false);
  const currentPoints = useRef<number[]>([]);
  const liveLineRef = useRef<Konva.Line>(null);

  const isDrawingTool = activeTool === "brush" || activeTool === "eraser";

  const handleMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (!isActive || !isDrawingTool) return;
      const pos = getCanvasPos(e);
      if (!pos) return;
      isDrawing.current = true;
      currentPoints.current = [pos.x, pos.y];
      if (liveLineRef.current) {
        liveLineRef.current.points([pos.x, pos.y]);
        liveLineRef.current.getLayer()?.batchDraw();
      }
    },
    [isActive, isDrawingTool],
  );

  const handleMouseMove = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (!isDrawing.current) return;
      const pos = getCanvasPos(e);
      if (!pos) return;
      currentPoints.current.push(pos.x, pos.y);
      if (liveLineRef.current) {
        liveLineRef.current.points([...currentPoints.current]);
        liveLineRef.current.getLayer()?.batchDraw();
      }
    },
    [],
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

  return (
    <>
      {strokes.map((stroke) => (
        <Line
          key={stroke.id}
          points={stroke.points}
          stroke={stroke.tool === "eraser" ? "#000000" : stroke.color}
          strokeWidth={stroke.strokeWidth}
          tension={0.5}
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
        tension={0.5}
        lineCap="round"
        lineJoin="round"
        globalCompositeOperation={activeTool === "eraser" ? "destination-out" : "source-over"}
        opacity={opacity}
        visible={visible && isDrawingTool}
        listening={false}
      />

      {/* Hit area for pointer events */}
      {isActive && isDrawingTool && (
        <Rect
          x={0}
          y={0}
          width={99999}
          height={99999}
          fill="transparent"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        />
      )}
    </>
  );
}
