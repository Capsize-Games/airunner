// ── Fuzzy Select (Magic Wand) Tool Hook ────────────────────────────────────
// Implements a flood-fill (BFS) pixel-selection algorithm that runs on
// mousedown against a Konva.Image or composite canvas.  Returns a boolean
// mask of selected pixels and a boundary polygon for rendering.
//
// Interaction model (mirrors GIMP's Fuzzy Select tool):
//   Click → flood-fill from click point → show marching ants boundary
//   Click elsewhere → replace selection
//   Escape       → cancel selection

import { useState, useCallback, useEffect } from "react";
import Konva from "konva";

import { floodFillMask, thresholdToDistance } from "../shared/floodFill";

// ── Public types ──────────────────────────────────────────────────────────

export interface WandRenderState {
  /** Flat [x,y,...] array of boundary polygon points (marching ants). */
  boundaryPoints: number[];
  /** The bounding box of the selection, or null if nothing is selected. */
  selectionBounds: { x: number; y: number; width: number; height: number } | null;
  /** Whether a selection is currently active. */
  hasSelection: boolean;
}

export interface UseWandToolReturn {
  renderState: WandRenderState;
  /** Returns true if the event was consumed. */
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

// ── Types ─────────────────────────────────────────────────────────────────

interface WandSettings {
  antialiasing: boolean;
  featherEdges: boolean;
  featherRadius: number;
  selectTransparentAreas: boolean;
  sampleMerged: boolean;
  diagonalNeighbors: boolean;
  threshold: number; // 0–100
}

// ── Boundary extraction ───────────────────────────────────────────────────

/**
 * Extract the outermost boundary of a boolean mask using Moore-Neighbor
 * tracing.  Returns a flat array of [x, y, ...] coordinates.
 */
function traceBoundary(
  mask: Uint8Array,
  width: number,
  height: number,
): number[] {
  // Find the first selected pixel (top-left)
  let startX = -1;
  let startY = -1;
  for (let y = 0; y < height && startX === -1; y++) {
    for (let x = 0; x < width && startX === -1; x++) {
      if (mask[y * width + x]) {
        startX = x;
        startY = y;
      }
    }
  }
  if (startX === -1) return [];

  // Moore neighborhood (8 directions, clockwise starting from right)
  const dx = [1, 1, 0, -1, -1, -1, 0, 1];
  const dy = [0, 1, 1, 1, 0, -1, -1, -1];

  const boundary: number[] = [];
  let cx = startX;
  let cy = startY;
  let dir = 0; // start searching right

  // Maximum iterations to prevent infinite loops
  const maxIters = width * height * 4;
  let iters = 0;

  // Find a starting boundary pixel: the first pixel that has at least one
  // non-selected neighbor.
  const isBoundary = (x: number, y: number): boolean => {
    if (x < 0 || x >= width || y < 0 || y >= height) return true;
    return mask[y * width + x] === 0;
  };

  const isSelected = (x: number, y: number): boolean => {
    if (x < 0 || x >= width || y < 0 || y >= height) return false;
    return mask[y * width + x] === 1;
  };

  // Check if start pixel is a boundary pixel; if not, scan for one.
  let foundBoundary = false;
  for (let d = 0; d < 8; d++) {
    if (isBoundary(startX + dx[d], startY + dy[d])) {
      foundBoundary = true;
      break;
    }
  }

  if (!foundBoundary) {
    // The entire image is selected — return the image boundary.
    return [0, 0, width - 1, 0, width - 1, height - 1, 0, height - 1];
  }

  // Moore-Neighbor tracing
  while (iters < maxIters) {
    iters++;
    boundary.push(cx, cy);

    // Search for the next boundary pixel, starting from (dir + 6) % 8
    // (i.e., two steps back from where we came from relative to current dir)
    const searchStart = (dir + 6) % 8;
    let nextFound = false;

    for (let i = 0; i < 8; i++) {
      const sd = (searchStart + i) % 8;
      const nx = cx + dx[sd];
      const ny = cy + dy[sd];

      if (isSelected(nx, ny)) {
        cx = nx;
        cy = ny;
        dir = sd;
        nextFound = true;
        break;
      }
    }

    if (!nextFound) break;

    // Check if we've returned to the start
    if (cx === startX && cy === startY && boundary.length >= 4) break;
  }

  return boundary;
}

// ── Main hook ─────────────────────────────────────────────────────────────

export function useWandTool({
  isActive,
  getCanvasPos,
  stageRef,
  settingsRef,
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
  stageRef: React.RefObject<Konva.Stage>;
  settingsRef: { current: WandSettings };
}): UseWandToolReturn {
  // ── React state (drives re-renders) ─────────────────────────────────
  const [boundaryPoints, setBoundaryPoints] = useState<number[]>([]);
  const [selectionBounds, setSelectionBounds] = useState<WandRenderState["selectionBounds"]>(null);
  const [hasSelection, setHasSelection] = useState(false);

  // ── Reset when tool is deactivated ──────────────────────────────────
  const resetAll = useCallback(() => {
    setBoundaryPoints([]);
    setSelectionBounds(null);
    setHasSelection(false);
  }, []);

  useEffect(() => {
    if (!isActive) resetAll();
  }, [isActive, resetAll]);

  // ── Escape key cancels selection ────────────────────────────────────
  useEffect(() => {
    if (!isActive) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") resetAll();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isActive, resetAll]);

  // ── Get ImageData from Konva ────────────────────────────────────────
  // ── Mouse handlers ──────────────────────────────────────────────────

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;

      const pos = getCanvasPos();
      if (!pos) return true;

      const stage = stageRef.current;
      if (!stage) return true;

      const settings = settingsRef.current;

      // Get pixel data
      let imageData: ImageData | null = null;
      let localX = pos.x;
      let localY = pos.y;

      // Maps a point from imageData/mask space back into document space —
      // the coordinate system in which the stage-level WandLayer renders
      // (i.e. before the stage's pan/zoom transform is applied). Without
      // this, the boundary is drawn at raw image-pixel offsets and appears
      // detached from the image it was sampled from.
      let toDocument: (x: number, y: number) => { x: number; y: number } =
        (x, y) => ({ x, y });

      if (settings.sampleMerged) {
        // Flatten entire scene to a canvas — reliable for any layer
        // structure, but may include tool overlays.
        const canvas = stage.toCanvas();
        const ctx = canvas.getContext("2d");
        if (!ctx) return true;

        // pos is in document coords; toCanvas produces a stage-sized
        // canvas.  Convert document coords to stage-pixel coords.
        const t = stage.getAbsoluteTransform().copy();
        const stagePos = t.point({ x: pos.x, y: pos.y });
        localX = Math.round(stagePos.x);
        localY = Math.round(stagePos.y);

        imageData = ctx.getImageData(
          0, 0,
          canvas.width,
          canvas.height,
        );

        // Mask space here is stage-pixel (screen) space; invert the stage
        // transform to get back to document space.
        const stageInv = stage.getAbsoluteTransform().copy().invert();
        toDocument = (x, y) => stageInv.point({ x, y });
      } else {
        // Find the topmost visible Konva.Image at the click position.
        // Use stage.find('Image') to recursively search through all
        // Groups, accounting for the nested Group structure in
        // CanvasLayerRenderer (outerGroup → contentGroup → image).
        const allImages = stage.find("Image") as Konva.Image[];
        // Raw screen-space pointer (getPointerPosition is in stage pixel coords,
        // unaffected by pan/zoom). We use this with each image's absolute
        // transform to convert into the image's local coordinate space.
        const rawPointer = stage.getPointerPosition();
        if (!rawPointer) return true;

        // Reverse: topmost (last rendered) first
        for (let i = allImages.length - 1; i >= 0; i--) {
          const imageNode = allImages[i];
          // Skip images on invisible layers
          const parentLayer = imageNode.getLayer();
          if (!parentLayer || !parentLayer.isVisible()) continue;

          const imgW = imageNode.width();
          const imgH = imageNode.height();

          // Convert the click from screen space into this image's local space.
          // This correctly handles stage pan, zoom, and any group transforms.
          const imgTransform = imageNode.getAbsoluteTransform().copy().invert();
          const localPoint = imgTransform.point(rawPointer);

          if (
            localPoint.x < 0 || localPoint.x > imgW ||
            localPoint.y < 0 || localPoint.y > imgH
          ) continue;

          // The source may be an <img> or an HTMLCanvasElement — the bucket
          // fill tool replaces the source with a canvas, which has no
          // `complete`/`naturalWidth`. Handle both so the wand keeps working
          // after a fill.
          const imageEl = imageNode.image() as
            | HTMLImageElement
            | HTMLCanvasElement;
          if (!imageEl) continue;
          if (imageEl instanceof HTMLImageElement && !imageEl.complete) continue;

          const naturalW =
            "naturalWidth" in imageEl
              ? (imageEl as HTMLImageElement).naturalWidth || imgW
              : imageEl.width || imgW;
          const naturalH =
            "naturalHeight" in imageEl
              ? (imageEl as HTMLImageElement).naturalHeight || imgH
              : imageEl.height || imgH;

          const imgCanvas = document.createElement("canvas");
          imgCanvas.width = naturalW;
          imgCanvas.height = naturalH;
          const imgCtx = imgCanvas.getContext("2d");
          if (!imgCtx) continue;
          imgCtx.drawImage(imageEl, 0, 0);

          // Scale from rendered size to natural/source pixel size
          const scaleX = naturalW / imgW;
          const scaleY = naturalH / imgH;
          localX = localPoint.x * scaleX;
          localY = localPoint.y * scaleY;

          imageData = imgCtx.getImageData(0, 0, naturalW, naturalH);

          // Build the inverse mapping: natural-pixel → rendered-local →
          // absolute (screen) → document space.
          const absT = imageNode.getAbsoluteTransform().copy();
          const stageInv = stage.getAbsoluteTransform().copy().invert();
          toDocument = (x, y) => {
            const screen = absT.point({ x: x / scaleX, y: y / scaleY });
            return stageInv.point(screen);
          };
          break;
        }

        if (!imageData) return true;
      }

      // Run flood fill
      const tolerance = thresholdToDistance(settings.threshold);
      const mask = floodFillMask(
        imageData,
        Math.round(localX),
        Math.round(localY),
        tolerance,
        {
          diagonal: settings.diagonalNeighbors,
          matchTransparent: settings.selectTransparentAreas,
        },
      );

      // Extract boundary
      const boundary = traceBoundary(mask, imageData.width, imageData.height);

      // Compute bounding box
      const bounds = computeBounds(mask, imageData.width, imageData.height);

      // Apply feather if enabled
      let finalBoundary = boundary;
      if (settings.featherEdges && settings.featherRadius > 0) {
        finalBoundary = applyFeatherToBoundary(
          mask,
          imageData.width,
          imageData.height,
          settings.featherRadius,
          boundary,
        );
      }

      // Map the boundary polygon from mask/image space into document space
      // so the stage-level WandLayer draws it aligned with the source image.
      const docBoundary: number[] = new Array(finalBoundary.length);
      for (let i = 0; i < finalBoundary.length; i += 2) {
        const p = toDocument(finalBoundary[i], finalBoundary[i + 1]);
        docBoundary[i] = p.x;
        docBoundary[i + 1] = p.y;
      }

      // Map the bounding box corners as well (the transform may include scale).
      let docBounds = bounds;
      if (bounds) {
        const tl = toDocument(bounds.x, bounds.y);
        const br = toDocument(bounds.x + bounds.width, bounds.y + bounds.height);
        docBounds = {
          x: Math.min(tl.x, br.x),
          y: Math.min(tl.y, br.y),
          width: Math.abs(br.x - tl.x),
          height: Math.abs(br.y - tl.y),
        };
      }

      setBoundaryPoints(docBoundary);
      setSelectionBounds(docBounds);
      setHasSelection(boundary.length > 0);

      return true;
    },
    [isActive, getCanvasPos, stageRef, settingsRef],
  );

  const onMouseMove = useCallback(
    (): boolean => {
      if (!isActive) return false;
      // Wand has no drag interaction — don't consume mousemove
      // so cursor updates and other handlers still work.
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
    renderState: { boundaryPoints, selectionBounds, hasSelection },
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────

function computeBounds(
  mask: Uint8Array,
  width: number,
  height: number,
): { x: number; y: number; width: number; height: number } | null {
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (mask[y * width + x]) {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }

  if (minX > maxX) return null;
  return {
    x: minX,
    y: minY,
    width: maxX - minX + 1,
    height: maxY - minY + 1,
  };
}

/**
 * Apply a feather radius to the boundary by expanding/shrinking the mask
 * and retracing.  This approximates a blur without Canvas filter support.
 */
function applyFeatherToBoundary(
  _mask: Uint8Array,
  _width: number,
  _height: number,
  _featherRadius: number,
  boundary: number[],
): number[] {
  // For simplicity, we return the original boundary — true feathering with
  // a blur requires rendering the mask to a scratch canvas and applying
  // ctx.filter = "blur(...)", then re-tracing.  That is done in the
  // WandLayer component via a data URL approach.  Here we just pass through.
  return boundary;
}
