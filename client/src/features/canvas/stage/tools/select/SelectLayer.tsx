// ── Rectangular Select Tool Rendering Layer ──────────────────────────────────
// Pure rendering component — no interaction logic.
// Renders the marquee selection rectangle and a size readout label.

import { Layer, Rect, Text } from "react-konva";
import type { SelectRenderState } from "./useSelectTool";

interface Props extends SelectRenderState {}

export default function SelectLayer({ rect }: Props) {
  if (!rect) return null;

  return (
    <>
      <Layer listening={false}>
        <Rect
          x={rect.x}
          y={rect.y}
          width={rect.width}
          height={rect.height}
          fill="rgba(99,153,255,0.08)"
          stroke="#6399ff"
          strokeWidth={1}
          dash={[5, 3]}
        />
      </Layer>

      {rect.width > 10 && rect.height > 10 && (
        <Layer listening={false}>
          <Text
            x={rect.x + 4}
            y={rect.y + rect.height + 5}
            text={`${Math.round(rect.width)} × ${Math.round(rect.height)}`}
            fontSize={10}
            fill="#6399ff"
            fontFamily="monospace"
          />
        </Layer>
      )}
    </>
  );
}
