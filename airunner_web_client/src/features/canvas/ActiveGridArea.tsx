import { useRef, useEffect } from "react";
import { Rect, Transformer, Group, Text } from "react-konva";
import Konva from "konva";
import type { ActiveGridArea as ActiveGridAreaType } from "./useCanvasState";
import { snapTo8, clamp } from "./canvasUtils";

interface ActiveGridAreaProps {
  area: ActiveGridAreaType;
  documentWidth: number;
  documentHeight: number;
  onChange: (area: ActiveGridAreaType) => void;
  snapToGrid?: boolean;
}

const SNAP = 8;

export default function ActiveGridArea({
  area,
  documentWidth,
  documentHeight,
  onChange,
  snapToGrid = false,
}: ActiveGridAreaProps) {
  const rectRef = useRef<Konva.Rect>(null);
  const trRef = useRef<Konva.Transformer>(null);

  // Attach Transformer to Rect
  useEffect(() => {
    if (rectRef.current && trRef.current) {
      trRef.current.nodes([rectRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, []);

  const snap = (val: number) => snapToGrid ? snapTo8(val) : snapTo8(val);

  const handleDragEnd = (e: Konva.KonvaEventObject<DragEvent>) => {
    const node = e.target;
    onChange({
      ...area,
      x: clamp(snap(node.x()), 0, documentWidth - area.width),
      y: clamp(snap(node.y()), 0, documentHeight - area.height),
    });
  };

  const handleTransformEnd = () => {
    const node = rectRef.current;
    if (!node) return;
    const scaleX = node.scaleX();
    const scaleY = node.scaleY();
    node.scaleX(1);
    node.scaleY(1);
    onChange({
      x: snap(node.x()),
      y: snap(node.y()),
      width: Math.max(SNAP, snap(node.width() * scaleX)),
      height: Math.max(SNAP, snap(node.height() * scaleY)),
    });
  };

  const label = `${area.width}×${area.height}  (${area.x}, ${area.y})`;

  return (
    <Group>
      <Rect
        ref={rectRef}
        x={area.x}
        y={area.y}
        width={area.width}
        height={area.height}
        fill="rgba(99,153,255,0.06)"
        stroke="#5599ff"
        strokeWidth={1.5}
        dash={[6, 3]}
        draggable
        onDragEnd={handleDragEnd}
        onTransformEnd={handleTransformEnd}
      />
      <Transformer
        ref={trRef}
        rotateEnabled={false}
        keepRatio={false}
        anchorSize={8}
        anchorFill="#5599ff"
        anchorStroke="#ffffff"
        anchorCornerRadius={2}
        borderStroke="#5599ff"
        borderDash={[4, 2]}
        boundBoxFunc={(_, newBox) => ({
          ...newBox,
          x: clamp(newBox.x, 0, documentWidth - newBox.width),
          y: clamp(newBox.y, 0, documentHeight - newBox.height),
          width: clamp(newBox.width, SNAP, documentWidth - newBox.x),
          height: clamp(newBox.height, SNAP, documentHeight - newBox.y),
        })}
      />
      <Text
        x={area.x + 4}
        y={area.y + area.height + 6}
        text={label}
        fontSize={10}
        fill="#5599ff"
        fontFamily="monospace"
        listening={false}
      />
    </Group>
  );
}
