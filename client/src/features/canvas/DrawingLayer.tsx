import { Line } from "react-konva";
import Konva from "konva";
import type { StrokeNode, ActiveTool } from "./useCanvasState";

interface DrawingLayerProps {
  strokes: StrokeNode[];
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  visible: boolean;
  opacity: number;
  isActive: boolean;
}

export default function DrawingLayer({
  strokes,
  activeTool,
  brushSize,
  brushColor,
  visible,
  opacity,
  isActive,
}: DrawingLayerProps) {
  const isDrawingTool = activeTool === "brush" || activeTool === "eraser";

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

      {/* Live preview line — managed imperatively by the stage overlay.
          Placed here so it renders inside the layer's offset <Group>. */}
      <Line
        ref={(node) => {
          if (isActive && isDrawingTool && node) {
            (window as unknown as Record<string, Konva.Line | undefined>)
              .__airunnerLiveStrokeRef = node;
          }
        }}
        points={[]}
        stroke={activeTool === "eraser" ? "#000000" : brushColor}
        strokeWidth={brushSize}
        lineCap="round"
        lineJoin="round"
        globalCompositeOperation={activeTool === "eraser" ? "destination-out" : "source-over"}
        opacity={opacity}
        visible={visible && isDrawingTool && isActive}
        listening={false}
      />
    </>
  );
}
