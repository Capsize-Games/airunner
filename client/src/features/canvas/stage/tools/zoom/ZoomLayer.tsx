// ── Zoom Marquee Layer ───────────────────────────────────────────────
// Renders a dashed selection rectangle during marquee zoom drag.
import { Layer, Rect } from "react-konva";
import type { ZoomRenderState } from "./useZoomTool";

type Props = ZoomRenderState;

export default function ZoomLayer({
  isDrawing,
  marqueeX,
  marqueeY,
  marqueeWidth,
  marqueeHeight,
}: Props) {
  if (!isDrawing) return null;

  // Only show after meaningful drag
  if (Math.abs(marqueeWidth) < 2 && Math.abs(marqueeHeight) < 2) {
    return null;
  }

  return (
    <Layer listening={false}>
      <Rect
        x={marqueeWidth > 0 ? marqueeX : marqueeX + marqueeWidth}
        y={marqueeHeight > 0 ? marqueeY : marqueeY + marqueeHeight}
        width={Math.abs(marqueeWidth)}
        height={Math.abs(marqueeHeight)}
        fill="rgba(99,153,255,0.08)"
        stroke="#6fa8ff"
        strokeWidth={1}
        dash={[6, 4]}
        strokeScaleEnabled={false}
      />
    </Layer>
  );
}
