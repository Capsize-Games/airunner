// ── Fuzzy Select (Magic Wand) Rendering Layer ─────────────────────────────
// Pure rendering component — no interaction logic.
// Draws the "marching ants" boundary around the selected pixel region.

import { Layer, Line } from "react-konva";
import type { WandRenderState } from "./useWandTool";

export default function WandLayer({
  boundaryPoints,
  hasSelection,
}: WandRenderState) {
  if (!hasSelection || boundaryPoints.length < 4) return null;

  // Static dash offset for marching ants effect
  const dashOffset = 0;

  return (
    <Layer listening={false}>
      {/* Thin outer highlight for contrast on dark/light backgrounds */}
      {boundaryPoints.length >= 6 && (
        <Line
          points={boundaryPoints}
          closed={true}
          tension={0}
          stroke="rgba(0,0,0,0.35)"
          strokeWidth={3}
          dash={[6, 4]}
          dashOffset={dashOffset}
          lineCap="round"
          lineJoin="round"
          strokeScaleEnabled={false}
        />
      )}
      {/* Selection outline — blue dashed "marching ants" */}
      {boundaryPoints.length >= 6 && (
        <Line
          points={boundaryPoints}
          closed={true}
          tension={0}
          fill="rgba(99,153,255,0.12)"
          stroke="rgba(99,153,255,0.85)"
          strokeWidth={1.5}
          dash={[6, 4]}
          dashOffset={dashOffset}
          lineCap="round"
          lineJoin="round"
          strokeScaleEnabled={false}
        />
      )}
    </Layer>
  );
}
