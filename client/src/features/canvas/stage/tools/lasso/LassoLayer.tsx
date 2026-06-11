// ── Lasso Tool Rendering Layer ───────────────────────────────────────────────
// Pure rendering component — no interaction logic.
// Receives LassoRenderState from useLassoTool and draws:
//   • The committed path (dashed while open, solid when closed)
//   • The in-progress freehand segment (while mouse is held)
//   • The rubber-band line (last anchor → cursor, between commits)
//   • A cursor dot (before the first anchor is placed)
//   • Anchor handle circles (first one highlighted; all larger when closed)

import { Layer, Line, Circle } from "react-konva";
import type { LassoRenderState } from "./useLassoTool";

interface Props extends LassoRenderState {
  /** Current stage zoom — keeps handle/cursor circles a constant screen size. */
  zoom: number;
}

export default function LassoLayer({
  points,
  freehandPoints,
  anchors,
  cursorPos,
  isClosed,
  zoom,
}: Props) {
  // Once closed, the committed selection is rendered by the shared
  // SelectionOverlay (persistent marching ants). This layer only draws the
  // in-progress path while the user is still building it.
  if (isClosed) return null;

  const hasAnchors  = anchors.length > 0;
  const lastAnchor  = hasAnchors ? anchors[anchors.length - 1] : null;
  const firstAnchor = hasAnchors ? anchors[0] : null;

  // Freehand line in progress.  When anchors exist, prepend the last one so
  // the segment visually connects; when starting from scratch, freehandPoints
  // already begins at the mousedown position.
  const freehandLine =
    freehandPoints.length >= 4
      ? lastAnchor
        ? [lastAnchor.x, lastAnchor.y, ...freehandPoints]
        : freehandPoints
      : null;

  // Rubber band: last anchor → cursor (only while mouse is up and not closed)
  const showRubberBand =
    !isClosed && hasAnchors && freehandPoints.length === 0 && cursorPos !== null;

  // Pulse the first anchor when cursor is near closing distance
  const nearClose =
    !isClosed &&
    firstAnchor !== null &&
    anchors.length >= 2 &&
    cursorPos !== null &&
    Math.hypot(cursorPos.x - firstAnchor.x, cursorPos.y - firstAnchor.y) < 12;

  // Skip the layer entirely if there is nothing to draw
  const nothingVisible =
    !cursorPos && points.length < 2 && !freehandLine && !hasAnchors;
  if (nothingVisible) return null;

  return (
    <Layer listening={false}>
      {/* Committed path */}
      {points.length >= 4 && (
        <Line
          points={points}
          closed={isClosed}
          tension={0}
          stroke="#6399ff"
          strokeWidth={1.5}
          dash={isClosed ? undefined : [5, 5]}
          fill={isClosed ? "rgba(99,153,255,0.12)" : undefined}
          strokeScaleEnabled={false}
        />
      )}

      {/* In-progress freehand drag segment */}
      {freehandLine && (
        <Line
          points={freehandLine}
          tension={0}
          stroke="#6399ff"
          strokeWidth={1.5}
          dash={[4, 4]}
          strokeScaleEnabled={false}
        />
      )}

      {/* Rubber band: last anchor → cursor (polygon mode) */}
      {showRubberBand && lastAnchor && cursorPos && (
        <Line
          points={[lastAnchor.x, lastAnchor.y, cursorPos.x, cursorPos.y]}
          stroke="#6399ff"
          strokeWidth={1}
          dash={[3, 4]}
          opacity={0.55}
          strokeScaleEnabled={false}
        />
      )}

      {/* Cursor dot — visible before the first anchor is placed */}
      {!hasAnchors && cursorPos && !freehandLine && (
        <Circle
          x={cursorPos.x}
          y={cursorPos.y}
          radius={3 / zoom}
          fill="#6399ff"
          opacity={0.6}
        />
      )}

      {/* Anchor handles */}
      {anchors.map((a, i) => {
        const isFirst   = i === 0;
        const highlight = isFirst && nearClose;
        return (
          <Circle
            key={i}
            x={a.x}
            y={a.y}
            radius={(highlight ? 6 : isClosed ? 5 : 3.5) / zoom}
            fill={isFirst ? "#6399ff" : "#fff"}
            stroke={highlight ? "#fff" : "#6399ff"}
            strokeWidth={1.5}
            opacity={highlight ? 0.9 : 1}
            strokeScaleEnabled={false}
          />
        );
      })}
    </Layer>
  );
}
