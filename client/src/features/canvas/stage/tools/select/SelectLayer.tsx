// ── Rectangular Select Tool Rendering Layer ──────────────────────────────────
// Pure rendering component — no interaction logic.
// Renders the marquee selection rectangle and a size readout label.

import { Layer, Rect, Text } from "react-konva";
import type { SelectRenderState } from "./useSelectTool";
import { useMarchingAnts } from "../shared/useMarchingAnts";

interface Props extends SelectRenderState {
  /** Current stage zoom — keeps the size readout a constant on-screen size. */
  zoom: number;
}

export default function SelectLayer({ rect, zoom }: Props) {
  // Animated dash offset — the "marching ants" effect.
  const dashOffset = useMarchingAnts();

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
          dashOffset={dashOffset}
          strokeScaleEnabled={false}
        />
      </Layer>

      {rect.width > 10 && rect.height > 10 && (
        <Layer listening={false}>
          <Text
            x={rect.x + 4 / zoom}
            y={rect.y + rect.height + 5 / zoom}
            text={`${Math.round(rect.width)} × ${Math.round(rect.height)}`}
            fontSize={10 / zoom}
            fill="#6399ff"
            fontFamily="monospace"
          />
        </Layer>
      )}
    </>
  );
}
