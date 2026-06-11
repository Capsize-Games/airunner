// ── Persistent Selection Overlay ──────────────────────────────────────────
// Renders the committed, tool-independent selection (from CanvasState) as
// animated "marching ants" in document space. Always mounted so the selection
// stays visible regardless of which tool is active, until "Select None".

import { Layer, Line } from "react-konva";
import type { SelectionData } from "../canvasTypes";
import { useMarchingAnts } from "./tools/shared/useMarchingAnts";

interface Props {
  selection: SelectionData | null;
}

export default function SelectionOverlay({ selection }: Props) {
  const dashOffset = useMarchingAnts();

  if (!selection || selection.points.length < 6) return null;
  const points = selection.points;

  return (
    <Layer listening={false}>
      {/* Dark backing for contrast on light/dark content */}
      <Line
        points={points}
        closed
        tension={0}
        stroke="rgba(0,0,0,0.4)"
        strokeWidth={3}
        dash={[6, 4]}
        dashOffset={dashOffset}
        lineCap="round"
        lineJoin="round"
        strokeScaleEnabled={false}
      />
      {/* Blue marching ants */}
      <Line
        points={points}
        closed
        tension={0}
        stroke="rgba(99,153,255,0.95)"
        strokeWidth={1.5}
        dash={[6, 4]}
        dashOffset={dashOffset}
        lineCap="round"
        lineJoin="round"
        strokeScaleEnabled={false}
      />
    </Layer>
  );
}
