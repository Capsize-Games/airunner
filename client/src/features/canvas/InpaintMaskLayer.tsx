import { useRef, useCallback } from "react";
import { Line, Rect, Group } from "react-konva";
import Konva from "konva";
import type { StrokeNode } from "./useCanvasState";

interface InpaintMaskLayerProps {
  strokes: StrokeNode[];
  brushSize: number;
  /** Pointer drawing happens when the mask brush or mask eraser is active. */
  drawingEnabled: boolean;
  /** True when the mask eraser (rather than the brush) is active. */
  eraser: boolean;
  documentWidth: number;
  documentHeight: number;
  onStrokeComplete: (stroke: Omit<StrokeNode, "id">) => void;
}

// Magenta in the UI; converted to a white-on-black mask before it's sent to the
// server. The masked (magenta) region is what gets regenerated.
//
// Both brush and eraser paint at full opacity (brush = source-over, eraser =
// destination-out). We deliberately do NOT use Group opacity — Konva pushes that
// down as a per-shape globalAlpha, which makes destination-out only erase ~50%
// per pass (requiring multiple passes) and the brush draw at partial opacity.
const MASK_COLOR = "#ff00ff";

function getCanvasPos(e: Konva.KonvaEventObject<MouseEvent>) {
  const stage = e.currentTarget.getStage();
  if (!stage) return null;
  const raw = stage.getPointerPosition();
  if (!raw) return null;
  const t = stage.getAbsoluteTransform().copy().invert();
  return t.point(raw);
}

export default function InpaintMaskLayer({
  strokes,
  brushSize,
  drawingEnabled,
  eraser,
  documentWidth,
  documentHeight,
  onStrokeComplete,
}: InpaintMaskLayerProps) {
  const isDrawing = useRef(false);
  const currentPoints = useRef<number[]>([]);
  const liveLineRef = useRef<Konva.Line>(null);

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
      color: MASK_COLOR,
      strokeWidth: brushSize,
      tool: eraser ? "eraser" : "brush",
    });
    currentPoints.current = [];
  }, [brushSize, eraser, onStrokeComplete]);

  return (
    <Group>
      {strokes.map((stroke) => (
        <Line
          key={stroke.id}
          points={stroke.points}
          stroke={MASK_COLOR}
          strokeWidth={stroke.strokeWidth}
          tension={0.5}
          lineCap="round"
          lineJoin="round"
          listening={false}
          globalCompositeOperation={
            stroke.tool === "eraser" ? "destination-out" : "source-over"
          }
        />
      ))}

      <Line
        ref={liveLineRef}
        points={[]}
        stroke={MASK_COLOR}
        strokeWidth={brushSize}
        tension={0.5}
        lineCap="round"
        lineJoin="round"
        listening={false}
        globalCompositeOperation={eraser ? "destination-out" : "source-over"}
      />

      {/* Hit area for drawing — only active while the inpaint-mask tool is on. */}
      {drawingEnabled && (
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
      )}
    </Group>
  );
}
