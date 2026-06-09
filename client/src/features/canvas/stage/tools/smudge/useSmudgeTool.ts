// ── Smudge Tool Hook ────────────────────────────────────────────────────
// Implements a GIMP-style smudge tool that smears pixels along the
// cursor path using raster operations on an off-screen canvas.
//
// Interaction model:
//   mousedown → grab ImageData from target Konva.Image, create
//     off-screen work canvas, sample brush pixels
//   mousemove → iteratively draw sampled brush along path onto
//     work canvas with alpha blending; update the Konva.Image
//     directly (throttled to 30 ms) for real-time visual feedback
//   mouseup   → commit work canvas back to Konva.Image, clear overlay

import { useState, useRef, useCallback, useEffect } from "react";
import Konva from "konva";

// ── Public types ──────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface SmudgeRenderState {
  /** Currently no visual overlay needed — updates go direct to the
   *  target Konva.Image for real-time feedback. */
}

export interface UseSmudgeToolReturn {
  renderState: SmudgeRenderState;
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

// ── Internal types ───────────────────────────────────────────────────────

interface SmudgeContext {
  /** Off-screen canvas holding the working copy of the image. */
  workCanvas: HTMLCanvasElement;
  /** 2D context of workCanvas. */
  workCtx: CanvasRenderingContext2D;
  /** Width of the work canvas (natural image width). */
  naturalW: number;
  /** Height of the work canvas (natural image height). */
  naturalH: number;
  /** Target Konva.Image node to update in real-time. */
  targetImage: Konva.Image;
  /** Width of the Konva.Image node. */
  imageW: number;
  /** Height of the Konva.Image node. */
  imageH: number;
  /** Ratio scaleX = naturalW / imageW for coordinate mapping. */
  scaleX: number;
  /** Ratio scaleY = naturalH / imageH for coordinate mapping. */
  scaleY: number;
}

interface SampledBrush {
  /** Width of the bounding box. */
  w: number;
  /** Height of the bounding box. */
  h: number;
  /** Pixel data (RGBA flat array) of the brush region. */
  data: Uint8ClampedArray;
  /** Offset X of the bounding box relative to the sample center. */
  ox: number;
  /** Offset Y of the bounding box relative to the sample center. */
  oy: number;
  /** Radius of the circular brush. */
  radius: number;
}

// ── Brush utilities ──────────────────────────────────────────────────────

/**
 * Sample a circular brush of pixels from the given ImageData around a
 * center point.  Returns the bounding box of the circle along with the
 * pixel data so it can be drawn elsewhere.
 */
function sampleBrush(
  imageData: ImageData,
  cx: number,
  cy: number,
  radius: number,
): SampledBrush | null {
  const r = Math.max(1, Math.round(radius));
  const d = r * 2;
  const ox = Math.round(cx) - r;
  const oy = Math.round(cy) - r;

  // Clamp bounding box to image bounds
  const x0 = Math.max(0, ox);
  const y0 = Math.max(0, oy);
  const x1 = Math.min(imageData.width, ox + d);
  const y1 = Math.min(imageData.height, oy + d);
  const w = x1 - x0;
  const h = y1 - y0;

  if (w <= 0 || h <= 0) return null;

  const src = imageData.data;
  const data = new Uint8ClampedArray(w * h * 4);
  const rr = r * r;

  for (let dy = 0; dy < h; dy++) {
    const gy = y0 + dy;
    for (let dx = 0; dx < w; dx++) {
      const gx = x0 + dx;
      const distSq = (gx - cx) * (gx - cx) + (gy - cy) * (gy - cy);
      const idx = (dy * w + dx) * 4;
      if (distSq <= rr) {
        const sIdx = (gy * imageData.width + gx) * 4;
        data[idx] = src[sIdx];
        data[idx + 1] = src[sIdx + 1];
        data[idx + 2] = src[sIdx + 2];
        data[idx + 3] = src[sIdx + 3];
      }
      // Outside circle: leave transparent
    }
  }

  return {
    w,
    h,
    data,
    ox: x0 - ox,
    oy: y0 - oy,
    radius: r,
  };
}

/**
 * "Stamp" a sampled brush onto an ImageData at a given center position,
 * blending each channel with the specified alpha (0–1).
 * Lower alpha → more trailing / fading effect.
 */
function stampBrush(
  imageData: ImageData,
  brush: SampledBrush,
  cx: number,
  cy: number,
  alpha: number,
): void {
  const { width, height, data: dst } = imageData;
  const src = brush.data;
  const bw = brush.w;
  const bh = brush.h;

  const dstX0 = Math.round(cx) - brush.radius + brush.ox;
  const dstY0 = Math.round(cy) - brush.radius + brush.oy;

  for (let dy = 0; dy < bh; dy++) {
    const dstY = dstY0 + dy;
    if (dstY < 0 || dstY >= height) continue;
    for (let dx = 0; dx < bw; dx++) {
      const dstX = dstX0 + dx;
      if (dstX < 0 || dstX >= width) continue;
      const sIdx = (dy * bw + dx) * 4;
      const sa = src[sIdx + 3];
      if (sa === 0) continue;

      const dIdx = (dstY * width + dstX) * 4;

      // Alpha blend: dst = src * alpha + dst * (1 - alpha)
      const na = sa * alpha / 255;
      dst[dIdx] = Math.round(
        src[sIdx] * na + dst[dIdx] * (1 - na),
      );
      dst[dIdx + 1] = Math.round(
        src[sIdx + 1] * na + dst[dIdx + 1] * (1 - na),
      );
      dst[dIdx + 2] = Math.round(
        src[sIdx + 2] * na + dst[dIdx + 2] * (1 - na),
      );
      // Preserve destination alpha for non-transparent pixels
      if (dst[dIdx + 3] > 0) {
        dst[dIdx + 3] = Math.max(
          dst[dIdx + 3],
          Math.round(src[sIdx + 3] * na),
        );
      }
    }
  }
}

// ── Interpolation ────────────────────────────────────────────────────────

function lerp(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  t: number,
): { x: number; y: number } {
  return { x: x1 + (x2 - x1) * t, y: y1 + (y2 - y1) * t };
}

/** Distance between two points. */
function dist(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  return Math.sqrt(dx * dx + dy * dy);
}

// ── Main hook ─────────────────────────────────────────────────────────────

const SMUDGE_ALPHA = 0.7; // Blend strength per stamp
const STEP_SPACING = 2; // Pixels between sample stamps
const KONVA_UPDATE_THROTTLE_MS = 30; // Min ms between Konva.Image updates

export function useSmudgeTool({
  isActive,
  getCanvasPos,
  stageRef,
  brushSize,
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
  stageRef: React.RefObject<Konva.Stage>;
  brushSize: number;
}): UseSmudgeToolReturn {
  // ── Render state (no visual overlay needed) ───────────────────────────
  const [renderState] = useState<SmudgeRenderState>({});

  // ── Refs for synchronous cross-handler access ─────────────────────────
  const ctxRef = useRef<SmudgeContext | null>(null);
  const brushRef = useRef<SampledBrush | null>(null);
  const isSmudgingRef = useRef(false);
  const lastPosRef = useRef<{ x: number; y: number } | null>(null);
  const lastKonvaUpdateRef = useRef(0);
  const workImageDataRef = useRef<ImageData | null>(null);

  // Keep brushSize in a ref so the synchronous path has the latest value
  const brushSizeRef = useRef(brushSize);
  useEffect(() => {
    brushSizeRef.current = brushSize;
  }, [brushSize]);

  // ── Flush work canvas to the real Konva.Image (throttled) ─────────────
  const flushToKonva = useCallback(() => {
    const now = performance.now();
    if (now - lastKonvaUpdateRef.current < KONVA_UPDATE_THROTTLE_MS) {
      return;
    }
    lastKonvaUpdateRef.current = now;

    const ctx = ctxRef.current;
    if (!ctx) return;

    // Apply the work canvas pixel data to the Konva.Image
    ctx.targetImage.image(ctx.workCanvas);
    ctx.targetImage.getLayer()?.batchDraw();
  }, []);

  // ── Reset state helpers ───────────────────────────────────────────────
  const resetSmudgeRefs = useCallback(() => {
    ctxRef.current = null;
    brushRef.current = null;
    isSmudgingRef.current = false;
    lastPosRef.current = null;
    workImageDataRef.current = null;
  }, []);

  // ── Deactivation reset ────────────────────────────────────────────────
  useEffect(() => {
    if (!isActive) {
      resetSmudgeRefs();
    }
  }, [isActive, resetSmudgeRefs]);

  // ── Global pointerup listener ─────────────────────────────────────────
  useEffect(() => {
    const onGlobalUp = () => {
      if (!isSmudgingRef.current) return;
      isSmudgingRef.current = false;

      const ctx = ctxRef.current;
      if (ctx) {
        // Final commit: write work canvas to Konva.Image
        ctx.targetImage.image(ctx.workCanvas);
        ctx.targetImage.getLayer()?.batchDraw();
      }

      resetSmudgeRefs();
    };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup", onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup", onGlobalUp);
    };
  }, [resetSmudgeRefs]);

  // ── Mouse handlers ────────────────────────────────────────────────────

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;

      const pos = getCanvasPos();
      if (!pos) return true;

      const stage = stageRef.current;
      if (!stage) return true;

      const radius = brushSizeRef.current / 2;
      if (radius <= 0) return true;

      // Find the topmost Konva.Image under the cursor
      const allImages = stage.find("Image") as Konva.Image[];
      const rawPointer = stage.getPointerPosition();
      if (!rawPointer) return true;

      let targetImage: Konva.Image | null = null;
      let imageData: ImageData | null = null;
      let naturalW = 1;
      let naturalH = 1;
      let imageW = 1;
      let imageH = 1;
      let localX = pos.x;
      let localY = pos.y;

      for (let i = allImages.length - 1; i >= 0; i--) {
        const imageNode = allImages[i];
        const parentLayer = imageNode.getLayer();
        if (!parentLayer || !parentLayer.isVisible()) continue;

        imageW = imageNode.width();
        imageH = imageNode.height();

        const imgTransform = imageNode
          .getAbsoluteTransform()
          .copy()
          .invert();
        const localPoint = imgTransform.point(rawPointer);

        if (
          localPoint.x < 0 || localPoint.x > imageW ||
          localPoint.y < 0 || localPoint.y > imageH
        ) continue;

        const imageEl = imageNode.image() as
          | HTMLImageElement
          | HTMLCanvasElement;
        if (!imageEl) continue;
        if (
          imageEl instanceof HTMLImageElement &&
          !imageEl.complete
        ) continue;

        naturalW =
          "naturalWidth" in imageEl
            ? (imageEl as HTMLImageElement).naturalWidth || imageW
            : imageEl.width || imageW;
        naturalH =
          "naturalHeight" in imageEl
            ? (imageEl as HTMLImageElement).naturalHeight || imageH
            : imageEl.height || imageH;

        const imgCanvas = document.createElement("canvas");
        imgCanvas.width = naturalW;
        imgCanvas.height = naturalH;
        const imgCtx = imgCanvas.getContext("2d");
        if (!imgCtx) continue;
        imgCtx.drawImage(imageEl, 0, 0);

        const scaleX = naturalW / imageW;
        const scaleY = naturalH / imageH;
        localX = localPoint.x * scaleX;
        localY = localPoint.y * scaleY;

        imageData = imgCtx.getImageData(0, 0, naturalW, naturalH);
        targetImage = imageNode;
        break;
      }

      if (!imageData || !targetImage) return true;

      // Create the work canvas (off-screen)
      const workCanvas = document.createElement("canvas");
      workCanvas.width = naturalW;
      workCanvas.height = naturalH;
      const workCtx = workCanvas.getContext("2d");
      if (!workCtx) return true;
      workCtx.putImageData(imageData, 0, 0);

      // Store context
      const ctx: SmudgeContext = {
        workCanvas,
        workCtx,
        naturalW,
        naturalH,
        targetImage,
        imageW,
        imageH,
        scaleX: naturalW / imageW,
        scaleY: naturalH / imageH,
      };
      ctxRef.current = ctx;
      isSmudgingRef.current = true;

      // Scale the brush radius to natural image coordinates
      const naturalRadius =
        radius * Math.max(ctx.scaleX, ctx.scaleY);

      // Sample the initial brush
      workImageDataRef.current = workCtx.getImageData(
        0,
        0,
        naturalW,
        naturalH,
      );
      const brush = sampleBrush(
        workImageDataRef.current,
        localX,
        localY,
        naturalRadius,
      );
      brushRef.current = brush;
      lastPosRef.current = { x: localX, y: localY };

      return true;
    },
    [isActive, getCanvasPos, stageRef],
  );

  const onMouseMove = useCallback(
    (): boolean => {
      if (!isActive || !isSmudgingRef.current) return false;

      const pos = getCanvasPos();
      if (!pos) return false;

      const ctx = ctxRef.current;
      if (!ctx) return false;

      const workData = workImageDataRef.current;
      if (!workData) return false;

      const brush = brushRef.current;
      const lastPos = lastPosRef.current;
      if (!brush || !lastPos) return false;

      // Convert cursor position to natural image coordinates
      const stage = stageRef.current;
      if (!stage) return false;
      const rawPointer = stage.getPointerPosition();
      if (!rawPointer) return false;

      const imgTransform = ctx.targetImage
        .getAbsoluteTransform()
        .copy()
        .invert();
      const localPoint = imgTransform.point(rawPointer);
      const curX = localPoint.x * ctx.scaleX;
      const curY = localPoint.y * ctx.scaleY;

      const naturalRadius =
        (brushSizeRef.current / 2) *
        Math.max(ctx.scaleX, ctx.scaleY);

      // Interpolate between last and current position
      const d = dist(lastPos.x, lastPos.y, curX, curY);
      const steps = Math.max(1, Math.ceil(d / STEP_SPACING));

      for (let i = 1; i <= steps; i++) {
        const t = i / steps;
        const mid = lerp(lastPos.x, lastPos.y, curX, curY, t);

        // Stamp the current brush sample at this interpolated point
        stampBrush(workData, brush, mid.x, mid.y, SMUDGE_ALPHA);

        // Re-sample the brush from the updated work image at the
        // new point to simulate "picking up" new paint
        const newBrush = sampleBrush(
          workData,
          mid.x,
          mid.y,
          naturalRadius,
        );
        if (newBrush) {
          brushRef.current = newBrush;
        }
      }

      // Write work data back to work canvas
      ctx.workCtx.putImageData(workData, 0, 0);

      lastPosRef.current = { x: curX, y: curY };

      // Update the Konva.Image directly (throttled) for real-time
      // visual feedback — no async image loading needed
      flushToKonva();

      return true;
    },
    [isActive, getCanvasPos, stageRef, flushToKonva],
  );

  const onMouseUp = useCallback(
    (): boolean => {
      if (!isActive || !isSmudgingRef.current) return false;

      isSmudgingRef.current = false;

      const ctx = ctxRef.current;
      if (ctx) {
        // Final commit: write work canvas to Konva.Image
        ctx.targetImage.image(ctx.workCanvas);
        ctx.targetImage.getLayer()?.batchDraw();
      }

      resetSmudgeRefs();

      return true;
    },
    [isActive, resetSmudgeRefs],
  );

  return {
    renderState,
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
