// ── Crop Tool Hook ───────────────────────────────────────────────────────
// Encapsulates interaction state and mouse / keyboard handlers for the
// crop tool.  The user draws a rectangle → dark overlay appears outside it →
// drag handles for resizing → Enter commits, Escape cancels.
//
// Two-way binding: crop rect values are synced to CanvasState so the
// settings sliders stay in lockstep.

import { useState, useRef, useCallback, useEffect } from "react";
import Konva from "konva";
import { useCanvasContext } from "../../../CanvasContext";

// ── Public types ─────────────────────────────────────────────────────────

export interface CropRenderState {
  /** The current crop rectangle in canvas-space coordinates. */
  cropX: number;
  cropY: number;
  cropWidth: number;
  cropHeight: number;
  /** Whether the crop box has been placed and is being adjusted. */
  isAdjusting: boolean;
}

export interface UseCropToolReturn {
  renderState: CropRenderState;
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp:   (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  /** Called by CropLayer when the Transformer modifies the crop rect. */
  onCropRectChange: (
    x: number, y: number,
    width: number, height: number,
  ) => void;
}

// ── Constants ────────────────────────────────────────────────────────────

const MIN_SIZE = 8; // px — minimum crop dimension

// ── Hook ─────────────────────────────────────────────────────────────────

export function useCropTool({
  isActive,
  getCanvasPos,
  stageRef,
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
  stageRef: React.RefObject<Konva.Stage>;
}): UseCropToolReturn {

  const canvas = useCanvasContext();

  // ── Local interaction state ────────────────────────────────────────
  const [isAdjusting, setIsAdjusting] = useState(false);
  const startRef = useRef<{ x: number; y: number } | null>(null);

  // ── Reset when tool is deactivated ─────────────────────────────────
  const resetCrop = useCallback(() => {
    startRef.current = null;
    setIsAdjusting(false);
    // No default selection — zero size keeps the overlay hidden until the
    // user actually draws a crop rectangle.
    canvas.setCropX(0);
    canvas.setCropY(0);
    canvas.setCropWidth(0);
    canvas.setCropHeight(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isActive) resetCrop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive]);

  // ── Commit the crop ──────────────────────────────────────────────
  const commitCrop = useCallback(() => {
    const cx = canvas.cropX;
    const cy = canvas.cropY;
    const cw = canvas.cropWidth;
    const ch = canvas.cropHeight;

    if (cw < MIN_SIZE || ch < MIN_SIZE) return;

    // Resize the document to the crop dimensions
    canvas.setDocumentSize(cw, ch);

    // Offset every layer so the cropped content shifts to origin
    for (const layer of canvas.layers) {
      canvas.moveLayer(
        layer.id,
        layer.offsetX - cx,
        layer.offsetY - cy,
      );
    }

    // Clear the crop rect and switch back to select
    canvas.setCropX(0);
    canvas.setCropY(0);
    canvas.setCropWidth(0);
    canvas.setCropHeight(0);
    canvas.setActiveTool("select");
  }, [canvas]);

  // ── Keyboard: Enter commits, Escape cancels ───────────────────────
  useEffect(() => {
    if (!isActive) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        canvas.setActiveTool("select");
        return;
      }
      if (e.key === "Enter") {
        commitCrop();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive, commitCrop]);

  // ── Global pointerup — catches releases outside the Stage ─────────
  useEffect(() => {
    const onGlobalUp = () => {
      if (startRef.current) {
        startRef.current = null;
      }
    };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup",   onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup",   onGlobalUp);
    };
  }, []);

  // ── Callback from CropLayer: Transformer updated the crop rect ───
  const onCropRectChange = useCallback(
    (x: number, y: number, width: number, height: number) => {
      canvas.setCropX(Math.round(x));
      canvas.setCropY(Math.round(y));
      canvas.setCropWidth(Math.max(MIN_SIZE, Math.round(width)));
      canvas.setCropHeight(Math.max(MIN_SIZE, Math.round(height)));
    },
    [canvas],
  );

  // ── Mouse handlers ───────────────────────────────────────────────

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;
      const pos = getCanvasPos();
      if (!pos) return true;

      // Start drawing a new crop rectangle. Size stays 0 until the pointer
      // actually moves — a bare click should not create a crop.
      startRef.current = { x: pos.x, y: pos.y };
      setIsAdjusting(false);
      canvas.setCropX(pos.x);
      canvas.setCropY(pos.y);
      canvas.setCropWidth(0);
      canvas.setCropHeight(0);
      return true;
    },
    [isActive, getCanvasPos, canvas],
  );

  const onMouseMove = useCallback(
    (): boolean => {
      if (!isActive) return false;
      if (!startRef.current) return true;

      const pos = getCanvasPos();
      if (!pos) return true;

      const sx = startRef.current.x;
      const sy = startRef.current.y;
      const nx = Math.min(sx, pos.x);
      const ny = Math.min(sy, pos.y);
      const nw = Math.abs(pos.x - sx);
      const nh = Math.abs(pos.y - sy);

      canvas.setCropX(nx);
      canvas.setCropY(ny);
      canvas.setCropWidth(nw);
      canvas.setCropHeight(nh);

      // Update cursor to crosshair during draw
      const container = stageRef.current?.container();
      if (container) container.style.cursor = "crosshair";

      return true;
    },
    [isActive, getCanvasPos, canvas, stageRef],
  );

  const onMouseUp = useCallback(
    (): boolean => {
      if (!isActive) return false;
      if (!startRef.current) return false;

      startRef.current = null;

      // Only keep the crop if the drag produced a sizable rect; otherwise a
      // click (or tiny drag) clears it back to nothing.
      if (
        canvas.cropWidth >= MIN_SIZE &&
        canvas.cropHeight >= MIN_SIZE
      ) {
        setIsAdjusting(true);
      } else {
        canvas.setCropWidth(0);
        canvas.setCropHeight(0);
      }

      return true;
    },
    [isActive, canvas.cropWidth, canvas.cropHeight],
  );

  // ── Build render state from context (keeps sliders in sync) ──────
  const renderState: CropRenderState = {
    cropX: canvas.cropX,
    cropY: canvas.cropY,
    cropWidth: canvas.cropWidth,
    cropHeight: canvas.cropHeight,
    isAdjusting,
  };

  return {
    renderState,
    onMouseDown,
    onMouseMove,
    onMouseUp,
    onCropRectChange,
  };
}
