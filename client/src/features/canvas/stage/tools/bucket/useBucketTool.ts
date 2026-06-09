// ── Bucket (Flood) Fill Tool Hook ──────────────────────────────────────
// Implements a BFS flood-fill pixel replacement algorithm that runs on
// mousedown against a Konva.Image.  Replaces the target color region
// with the selected foreground or background fill color.
//
// Interaction model (mirrors GIMP's Bucket Fill tool):
//   Click → flood-fill from click point → replace color
//   Click elsewhere → fill new region

import { useState, useCallback, useEffect } from "react";
import Konva from "konva";

import { floodFillMask, thresholdToDistance } from "../shared/floodFill";

// ── Public types ──────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface BucketRenderState {
  /** Currently no visual overlay needed for bucket fill. */
}

export interface UseBucketToolReturn {
  renderState: BucketRenderState;
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

// ── Types ─────────────────────────────────────────────────────────────────

interface BucketSettings {
  colorSource: "foreground" | "background";
  fillTransparentAreas: boolean;
  antialiasing: boolean;
  threshold: number; // 0–100
}

// ── Color utilities ───────────────────────────────────────────────────────

/** Parse a CSS hex color (#rrggbb or #rgb) into [R, G, B, A]. */
function hexToRgba(hex: string): [number, number, number, number] {
  const trimmed = hex.replace(/^#/, "");
  let r: number;
  let g: number;
  let b: number;
  if (trimmed.length === 3) {
    r = parseInt(trimmed[0] + trimmed[0], 16);
    g = parseInt(trimmed[1] + trimmed[1], 16);
    b = parseInt(trimmed[2] + trimmed[2], 16);
  } else {
    r = parseInt(trimmed.substring(0, 2), 16);
    g = parseInt(trimmed.substring(2, 4), 16);
    b = parseInt(trimmed.substring(4, 6), 16);
  }
  return [r, g, b, 255];
}

// ── Fill application ───────────────────────────────────────────────────────

/** Write a solid fill color over every pixel marked in the mask. */
function writeFill(
  imageData: ImageData,
  mask: Uint8Array,
  fillColor: [number, number, number, number],
): void {
  const { data } = imageData;
  for (let p = 0; p < mask.length; p++) {
    if (!mask[p]) continue;
    const idx = p * 4;
    data[idx] = fillColor[0];
    data[idx + 1] = fillColor[1];
    data[idx + 2] = fillColor[2];
    data[idx + 3] = fillColor[3];
  }
}

/**
 * Apply antialiasing to the boundary of the filled region.
 * Blends the original pixel color with the fill color at edges.
 */
function applyAntialiasing(
  imageData: ImageData,
  mask: Uint8Array,
  fillColor: [number, number, number, number],
): void {
  const { width, height, data } = imageData;

  // Find boundary pixels: filled pixels with at least one non-filled neighbor
  const boundary = new Uint8Array(width * height);
  const dx = [0, 1, 0, -1, 1, 1, -1, -1];
  const dy = [-1, 0, 1, 0, -1, 1, 1, -1];

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const p = y * width + x;
      if (!mask[p]) continue;
      for (let d = 0; d < 8; d++) {
        const nx = x + dx[d];
        const ny = y + dy[d];
        if (nx < 0 || nx >= width || ny < 0 || ny >= height) {
          boundary[p] = 1;
          break;
        }
        if (!mask[ny * width + nx]) {
          boundary[p] = 1;
          break;
        }
      }
    }
  }

  // Dilate boundary outward by 1 pixel for feather blend
  const feather = new Uint8Array(width * height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const p = y * width + x;
      if (boundary[p]) {
        feather[p] = 1;
        continue;
      }
      // Check if any neighbor is a boundary pixel
      for (let d = 0; d < 8; d++) {
        const nx = x + dx[d];
        const ny = y + dy[d];
        if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;
        if (boundary[ny * width + nx]) {
          feather[p] = 1;
          break;
        }
      }
    }
  }

  // Apply 50% blend for feather pixels
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const p = y * width + x;
      if (!feather[p]) continue;
      const idx = p * 4;
      data[idx] = Math.round(
        (data[idx] + fillColor[0]) / 2,
      );
      data[idx + 1] = Math.round(
        (data[idx + 1] + fillColor[1]) / 2,
      );
      data[idx + 2] = Math.round(
        (data[idx + 2] + fillColor[2]) / 2,
      );
      // Keep alpha at 255 for filled pixels
      if (mask[p]) {
        data[idx + 3] = 255;
      }
    }
  }
}

// ── Main hook ─────────────────────────────────────────────────────────────

export function useBucketTool({
  isActive,
  getCanvasPos,
  stageRef,
  settingsRef,
  foregroundColor,
  backgroundColor,
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
  stageRef: React.RefObject<Konva.Stage>;
  settingsRef: { current: BucketSettings };
  foregroundColor: string;
  backgroundColor: string;
}): UseBucketToolReturn {
  // The bucket tool has no persistent visual overlay
  const [renderState] = useState<BucketRenderState>({});

  // Reset when deactivated
  useEffect(() => {
    if (!isActive) { /* no state to reset */ }
  }, [isActive]);

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;

      const pos = getCanvasPos();
      if (!pos) return true;

      const stage = stageRef.current;
      if (!stage) return true;

      const settings = settingsRef.current;

      // Determine fill color
      const colorHex =
        settings.colorSource === "foreground"
          ? foregroundColor
          : backgroundColor;
      const fillColor = hexToRgba(colorHex);

      // Find the target Konva.Image
      let localX = pos.x;
      let localY = pos.y;
      let targetImage: Konva.Image | null = null;
      let imageData: ImageData | null = null;
      let naturalW = 1;
      let naturalH = 1;

      const allImages = stage.find("Image") as Konva.Image[];
      const rawPointer = stage.getPointerPosition();
      if (!rawPointer) return true;

      // Reverse: topmost first
      for (let i = allImages.length - 1; i >= 0; i--) {
        const imageNode = allImages[i];
        const parentLayer = imageNode.getLayer();
        if (!parentLayer || !parentLayer.isVisible()) continue;

        const imgW = imageNode.width();
        const imgH = imageNode.height();

        const imgTransform = imageNode
          .getAbsoluteTransform()
          .copy()
          .invert();
        const localPoint = imgTransform.point(rawPointer);

        if (
          localPoint.x < 0 || localPoint.x > imgW ||
          localPoint.y < 0 || localPoint.y > imgH
        ) continue;

        const imageEl = imageNode.image() as
          | HTMLImageElement
          | HTMLCanvasElement;
        if (!imageEl) continue;
        // HTMLCanvasElement may not have 'complete'
        if (
          imageEl instanceof HTMLImageElement &&
          !imageEl.complete
        ) continue;

        naturalW =
          "naturalWidth" in imageEl
            ? (imageEl as HTMLImageElement).naturalWidth || imgW
            : imageEl.width || imgW;
        naturalH =
          "naturalHeight" in imageEl
            ? (imageEl as HTMLImageElement).naturalHeight || imgH
            : imageEl.height || imgH;

        const imgCanvas = document.createElement("canvas");
        imgCanvas.width = naturalW;
        imgCanvas.height = naturalH;
        const imgCtx = imgCanvas.getContext("2d");
        if (!imgCtx) continue;
        imgCtx.drawImage(imageEl, 0, 0);

        const scaleX = naturalW / imgW;
        const scaleY = naturalH / imgH;
        localX = localPoint.x * scaleX;
        localY = localPoint.y * scaleY;

        imageData = imgCtx.getImageData(0, 0, naturalW, naturalH);
        targetImage = imageNode;
        break;
      }

      if (!imageData || !targetImage) return true;

      // Compute the fill region, then write the fill color over it.
      // Using a mask-only flood fill (shared with the wand tool) keeps the
      // seed color stable during traversal — writing during the BFS would
      // corrupt the comparison reference.
      const tolerance = thresholdToDistance(settings.threshold);
      const mask = floodFillMask(
        imageData,
        Math.round(localX),
        Math.round(localY),
        tolerance,
        { matchTransparent: settings.fillTransparentAreas },
      );

      writeFill(imageData, mask, fillColor);

      // Apply antialiasing if enabled
      if (settings.antialiasing) {
        applyAntialiasing(imageData, mask, fillColor);
      }

      // Write the modified ImageData back to the target image
      const writeCanvas = document.createElement("canvas");
      writeCanvas.width = naturalW;
      writeCanvas.height = naturalH;
      const writeCtx = writeCanvas.getContext("2d");
      if (!writeCtx) return true;
      writeCtx.putImageData(imageData, 0, 0);

      // Update the Konva.Image's image source
      targetImage.image(writeCanvas);
      targetImage.getLayer()?.batchDraw();

      return true;
    },
    [
      isActive,
      getCanvasPos,
      stageRef,
      settingsRef,
      foregroundColor,
      backgroundColor,
    ],
  );

  const onMouseMove = useCallback(
    (): boolean => {
      if (!isActive) return false;
      return false;
    },
    [isActive],
  );

  const onMouseUp = useCallback(
    (): boolean => {
      if (!isActive) return false;
      return true;
    },
    [isActive],
  );

  return {
    renderState,
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
