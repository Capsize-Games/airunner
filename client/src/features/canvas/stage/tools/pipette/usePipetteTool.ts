// ── Pipette (Color Picker / Eyedropper) Tool Hook ─────────────────────
// Click anywhere on the canvas to sample the exact pixel color under the
// cursor and set it as the active foreground or background color.
//
// Interaction model:
//   mousedown → get pointer position, composite stage to canvas, read
//     1×1 pixel RGBA data, convert to hex, update global color state.

import { useRef, useCallback, useEffect, useState } from "react";
import Konva from "konva";

// ── Public types ──────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface PipetteRenderState {
  /** No visual overlay needed — color is read and applied on click. */
}

export interface UsePipetteToolReturn {
  renderState: PipetteRenderState;
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────

/**
 * Convert RGBA byte values to a CSS hex string (#RRGGBB).
 * Ignores alpha — the picker samples composite color.
 */
function rgbaToHex(r: number, g: number, b: number): string {
  const toHex = (n: number) =>
    Math.max(0, Math.min(255, n)).toString(16).padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

// ── Main hook ─────────────────────────────────────────────────────────────

export function usePipetteTool({
  isActive,
  stageRef,
  pipetteTarget,
  onSetForegroundColor,
  onSetBackgroundColor,
}: {
  isActive: boolean;
  stageRef: React.RefObject<Konva.Stage>;
  pipetteTarget: "foreground" | "background";
  onSetForegroundColor: (color: string) => void;
  onSetBackgroundColor: (color: string) => void;
}): UsePipetteToolReturn {
  // ── Render state (no visual overlay needed) ───────────────────────────
  const [renderState] = useState<PipetteRenderState>({});

  // Keep pipetteTarget in a ref so the synchronous handler always has the
  // latest value without needing it as a callback dependency.
  const pipetteTargetRef = useRef(pipetteTarget);
  useEffect(() => {
    pipetteTargetRef.current = pipetteTarget;
  }, [pipetteTarget]);

  // ── Reset when deactivated ────────────────────────────────────────────
  useEffect(() => {
    if (!isActive) {
      // Nothing to clean up for this tool
    }
  }, [isActive]);

  // ── Global pointerup listener (no-op for pipette) ─────────────────────
  useEffect(() => {
    const onGlobalUp = () => {
      // Pipette works on click, not drag — no global state to manage.
    };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup", onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup", onGlobalUp);
    };
  }, []);

  // ── Mouse handlers ────────────────────────────────────────────────────

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;

      const stage = stageRef.current;
      if (!stage) return true;

      // Sample using the raw pointer position. stage.toCanvas() renders in
      // screen/stage-pixel space, which is the same space getPointerPosition()
      // reports — NOT the document space returned by getCanvasPos(). Using
      // document coords here would read the wrong pixel whenever the canvas is
      // panned or zoomed.
      const rawPointer = stage.getPointerPosition();
      if (!rawPointer) return true;

      // Composite the full stage to a canvas and read the 1×1 pixel
      // under the cursor.
      let canvas: HTMLCanvasElement;
      try {
        canvas = stage.toCanvas();
      } catch {
        return true;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return true;

      let pixelData: Uint8ClampedArray;
      try {
        pixelData = ctx.getImageData(
          Math.round(rawPointer.x),
          Math.round(rawPointer.y),
          1,
          1,
        ).data;
      } catch {
        // Outside the canvas bounds or security error
        return true;
      }

      // Convert RGBA to hex (ignore alpha — we read the composited pixel)
      const hex = rgbaToHex(pixelData[0], pixelData[1], pixelData[2]);

      // Route to the target color slot
      if (pipetteTargetRef.current === "foreground") {
        onSetForegroundColor(hex);
      } else {
        onSetBackgroundColor(hex);
      }

      return true;
    },
    [isActive, stageRef, onSetForegroundColor, onSetBackgroundColor],
  );

  const onMouseMove = useCallback(
    (): boolean => {
      // Pipette only samples on click — no move handling needed.
      return false;
    },
    [],
  );

  const onMouseUp = useCallback(
    (): boolean => {
      // Pipette only samples on click — no up handling needed.
      return false;
    },
    [],
  );

  return {
    renderState,
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
