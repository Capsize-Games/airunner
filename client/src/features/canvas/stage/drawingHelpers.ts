// ── Canvas Stage Drawing Helpers ────────────────────────────────────────
// Pure math utilities shared between CanvasStage and DrawingLayer.

import Konva from "konva";

export const INTERP_THRESHOLD = 3;

export function lerp(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  t: number,
): { x: number; y: number } {
  return { x: x1 + (x2 - x1) * t, y: y1 + (y2 - y1) * t };
}

export function clampToDoc(
  x: number,
  y: number,
  w: number,
  h: number,
  inset: number,
  offsetX = 0,
  offsetY = 0,
): { x: number; y: number } {
  return {
    x: Math.max(
      inset - offsetX,
      Math.min(w - inset - offsetX, x),
    ),
    y: Math.max(
      inset - offsetY,
      Math.min(h - inset - offsetY, y),
    ),
  };
}

// Cohen–Sutherland line clipping region codes.
const CS_INSIDE = 0;
const CS_LEFT = 1;
const CS_RIGHT = 2;
const CS_BOTTOM = 4;
const CS_TOP = 8;

function csCode(
  x: number,
  y: number,
  xmin: number,
  ymin: number,
  xmax: number,
  ymax: number,
): number {
  let code = CS_INSIDE;
  if (x < xmin) code |= CS_LEFT;
  else if (x > xmax) code |= CS_RIGHT;
  if (y < ymin) code |= CS_TOP;
  else if (y > ymax) code |= CS_BOTTOM;
  return code;
}

/**
 * Clip a polyline (flat [x1,y1, x2,y2, ...] array) to the rectangle
 * [xmin, ymin, xmax, ymax] using the Cohen–Sutherland algorithm.
 * Segments entirely outside the rect are dropped; segments crossing the
 * boundary are clipped at the exact intersection point.
 *
 * Used when committing brush strokes (handleOverlayPointerUp) so that
 * only the portions of a stroke intersecting the document bounds are
 * saved — off-canvas drawing never persists on the layer.
 * [xmin, ymin, xmax, ymax]. Segments entirely outside are dropped;
 * segments crossing the boundary are clipped at the intersection.
 * Returns a new flat array of points.
 */
export function clipPointsToRect(
  points: number[],
  xmin: number,
  ymin: number,
  xmax: number,
  ymax: number,
): number[] {
  const out: number[] = [];
  for (let i = 0; i < points.length - 2; i += 2) {
    let x0 = points[i];
    let y0 = points[i + 1];
    let x1 = points[i + 2];
    let y1 = points[i + 3];
    let c0 = csCode(x0, y0, xmin, ymin, xmax, ymax);
    let c1 = csCode(x1, y1, xmin, ymin, xmax, ymax);

    while (true) {
      if ((c0 | c1) === CS_INSIDE) {
        if (
          out.length === 0 ||
          out[out.length - 2] !== x0 ||
          out[out.length - 1] !== y0
        ) {
          out.push(x0, y0);
        }
        out.push(x1, y1);
        break;
      }
      if ((c0 & c1) !== CS_INSIDE) {
        break; // both outside same side — reject
      }
      const codeOut = c0 !== CS_INSIDE ? c0 : c1;
      let x = 0;
      let y = 0;
      if (codeOut & CS_TOP) {
        x = x0 + ((x1 - x0) * (ymin - y0)) / (y1 - y0);
        y = ymin;
      } else if (codeOut & CS_BOTTOM) {
        x = x0 + ((x1 - x0) * (ymax - y0)) / (y1 - y0);
        y = ymax;
      } else if (codeOut & CS_RIGHT) {
        y = y0 + ((y1 - y0) * (xmax - x0)) / (x1 - x0);
        x = xmax;
      } else {
        // LEFT
        y = y0 + ((y1 - y0) * (xmin - x0)) / (x1 - x0);
        x = xmin;
      }
      if (codeOut === c0) {
        x0 = x;
        y0 = y;
        c0 = csCode(x0, y0, xmin, ymin, xmax, ymax);
      } else {
        x1 = x;
        y1 = y;
        c1 = csCode(x1, y1, xmin, ymin, xmax, ymax);
      }
    }
  }
  return out;
}

export function getCanvasPosFromStage(
  stage: Konva.Stage | null,
) {
  if (!stage) return null;
  const raw = stage.getPointerPosition();
  if (!raw) return null;
  const t = stage.getAbsoluteTransform().copy().invert();
  return t.point(raw);
}
