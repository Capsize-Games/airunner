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
  /** When false the area is display-only (no drag/resize, passes pointer events
   *  through) so it doesn't block drawing tools. */
  interactive?: boolean;
}

const MIN_SNAP = 8;   // generation constraint — always applied
const VIS_SNAP = 16;  // visual grid — applied when snapToGrid is on

export default function ActiveGridArea({
  area,
  documentWidth,
  documentHeight,
  onChange,
  snapToGrid = false,
  interactive = true,
}: ActiveGridAreaProps) {
  const rectRef = useRef<Konva.Rect>(null);
  const trRef = useRef<Konva.Transformer>(null);

  // Attach Transformer to Rect (only while interactive — the Transformer is
  // unmounted otherwise).
  useEffect(() => {
    if (interactive && rectRef.current && trRef.current) {
      trRef.current.nodes([rectRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [interactive]);

  // Snap to 16px visual grid when enabled, otherwise fine 8px constraint
  const snap = (val: number) =>
    snapToGrid
      ? Math.round(val / VIS_SNAP) * VIS_SNAP
      : snapTo8(val);

  const handleDragEnd = (e: Konva.KonvaEventObject<DragEvent>) => {
    const node = e.target;
    const sx = clamp(snap(node.x()), 0, documentWidth  - area.width);
    const sy = clamp(snap(node.y()), 0, documentHeight - area.height);
    // Move the Konva node to the snapped position immediately so it doesn't jump on re-render
    node.x(sx);
    node.y(sy);
    onChange({ ...area, x: sx, y: sy });
  };

  const handleTransformEnd = () => {
    const node = rectRef.current;
    if (!node) return;
    const scaleX = node.scaleX();
    const scaleY = node.scaleY();
    node.scaleX(1);
    node.scaleY(1);
    // node.x()/width() are in document space (the layer carries the zoom), so
    // clamp here rather than in boundBoxFunc (which works in screen space).
    const nw = Math.min(documentWidth, Math.max(MIN_SNAP, snap(node.width() * scaleX)));
    const nh = Math.min(documentHeight, Math.max(MIN_SNAP, snap(node.height() * scaleY)));
    const nx = clamp(snap(node.x()), 0, documentWidth - nw);
    const ny = clamp(snap(node.y()), 0, documentHeight - nh);
    node.x(nx); node.y(ny); node.width(nw); node.height(nh);
    onChange({ x: nx, y: ny, width: nw, height: nh });
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
        listening={interactive}
        draggable={interactive}
        onDragEnd={handleDragEnd}
        onTransformEnd={handleTransformEnd}
      />
      {interactive && (
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
          boundBoxFunc={(oldBox, newBox) => {
            // newBox is in absolute (screen) coordinates; only guard against
            // collapse/inversion. Document-bounds clamping + snapping happen in
            // handleTransformEnd using local coordinates.
            if (newBox.width < MIN_SNAP || newBox.height < MIN_SNAP) {
              return oldBox;
            }
            return newBox;
          }}
        />
      )}
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
