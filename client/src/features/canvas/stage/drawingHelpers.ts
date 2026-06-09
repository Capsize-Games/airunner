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

export function getCanvasPosFromStage(
  stage: Konva.Stage | null,
) {
  if (!stage) return null;
  const raw = stage.getPointerPosition();
  if (!raw) return null;
  const t = stage.getAbsoluteTransform().copy().invert();
  return t.point(raw);
}
