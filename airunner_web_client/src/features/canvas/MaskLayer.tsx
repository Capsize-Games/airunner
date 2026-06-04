import { useRef, useCallback } from "react";
import { Line, Rect, Group } from "react-konva";
import Konva from "konva";
import type { StrokeNode, ActiveTool } from "./useCanvasState";

interface MaskLayerProps {
  strokes: StrokeNode[];
  brushSize: number;
  activeTool: ActiveTool;
  documentWidth: number;
  documentHeight: number;
  onStrokeComplete: (stroke: Omit<StrokeNode, "id">) => void;
}

function getCanvasPos(e: Konva.KonvaEventObject<MouseEvent>) {
  const stage = e.currentTarget.getStage();
  if (!stage) return null;
  const raw = stage.getPointerPosition();
  if (!raw) return null;
  const t = stage.getAbsoluteTransform().copy().invert();
  return t.point(raw);
}

export default function MaskLayer({
  strokes,
  brushSize,
  activeTool,
  documentWidth,
  documentHeight,
  onStrokeComplete,
}: MaskLayerProps) {
  const isDrawing = useRef(false);
  const currentPoints = useRef<number[]>([]);
  const liveLineRef = useRef<Konva.Line>(null);

  // When mask tool: draw white (add to mask).
  // When eraser tool: draw black (erase from mask).
  const strokeColor = activeTool === "eraser" ? "#000000" : "#ffffff";

  const handleMouseDown = useCallback((e: Konva.KonvaEventObject<MouseEvent>) => {
    const pos = getCanvasPos(e);
    if (!pos) return;
    isDrawing.current = true;
    currentPoints.current = [pos.x, pos.y];
    if (liveLineRef.current) {
      liveLineRef.current.points([pos.x, pos.y]);
      liveLineRef.current.getLayer()?.batchDraw();
    }
  }, []);

  const handleMouseMove = useCallback((e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!isDrawing.current) return;
    const pos = getCanvasPos(e);
    if (!pos) return;
    currentPoints.current.push(pos.x, pos.y);
    if (liveLineRef.current) {
      liveLineRef.current.points([...currentPoints.current]);
      liveLineRef.current.getLayer()?.batchDraw();
    }
  }, []);

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
      color: strokeColor,
      strokeWidth: brushSize,
      tool: "brush",
    });
    currentPoints.current = [];
  }, [brushSize, strokeColor, onStrokeComplete]);

  return (
    <Group>
      {/* Black background clipped to document bounds */}
      <Rect x={0} y={0} width={documentWidth} height={documentHeight} fill="#000000" />

      {strokes.map((stroke) => (
        <Line
          key={stroke.id}
          points={stroke.points}
          stroke={stroke.color}
          strokeWidth={stroke.strokeWidth}
          tension={0.5}
          lineCap="round"
          lineJoin="round"
        />
      ))}

      <Line
        ref={liveLineRef}
        points={[]}
        stroke={strokeColor}
        strokeWidth={brushSize}
        tension={0.5}
        lineCap="round"
        lineJoin="round"
        listening={false}
      />

      {/* Hit area limited to document bounds */}
      <Rect
        x={0}
        y={0}
        width={documentWidth}
        height={documentHeight}
        fill="transparent"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
    </Group>
  );
}
