// ── Zoom Tool Interaction Hook ────────────────────────────────────────
// Manages marquee zoom rectangle drawing and click zoom interactions.
import { useState, useRef, useCallback, useEffect } from "react";
import Konva from "konva";

const CLICK_THRESHOLD = 3; // px — movement below this is treated as click
const ZOOM_FACTOR = 1.2;

// ── Render state ─────────────────────────────────────────────────────

export interface ZoomRenderState {
  isDrawing: boolean;
  marqueeX: number;
  marqueeY: number;
  marqueeWidth: number;
  marqueeHeight: number;
}

// ── Hook return type ──────────────────────────────────────────────────

export interface UseZoomToolReturn {
  renderState: ZoomRenderState;
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

// ── Hook ──────────────────────────────────────────────────────────────

export function useZoomTool({
  isActive,
  getCanvasPos,
  stageRef,
  zoomDirection,
  onZoomApplied,
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
  stageRef: React.RefObject<Konva.Stage>;
  zoomDirection: "in" | "out";
  /**
   * Called after the tool changes the stage scale, so the host can sync the
   * canonical zoom state (footer percentage) and disable fit-to-view — without
   * which a resize would re-fit and discard the tool's zoom.
   */
  onZoomApplied: (scale: number) => void;
}): UseZoomToolReturn {
  const [marqueeX, setMarqueeX] = useState(0);
  const [marqueeY, setMarqueeY] = useState(0);
  const [marqueeWidth, setMarqueeWidth] = useState(0);
  const [marqueeHeight, setMarqueeHeight] = useState(0);
  const [isDrawing, setIsDrawing] = useState(false);

  const startPosRef = useRef({ x: 0, y: 0 });
  const dragStartedRef = useRef(false);
  const marqueeWidthRef = useRef(0);
  const marqueeHeightRef = useRef(0);

  // Reset when tool is deactivated
  useEffect(() => {
    if (!isActive) {
      dragStartedRef.current = false;
    }
  }, [isActive]);

  // ── Shared zoom helpers ──────────────────────────────────────────

  const doClickZoom = useCallback(
    (pointer: { x: number; y: number }) => {
      const stage = stageRef.current;
      if (!stage) return;
      const oldScale = stage.scaleX();
      const newScale =
        zoomDirection === "in"
          ? oldScale * ZOOM_FACTOR
          : oldScale / ZOOM_FACTOR;
      const clamped = Math.max(0.05, Math.min(newScale, 20));
      const mousePointTo = {
        x: (pointer.x - stage.x()) / oldScale,
        y: (pointer.y - stage.y()) / oldScale,
      };
      stage.scale({ x: clamped, y: clamped });
      stage.position({
        x: pointer.x - mousePointTo.x * clamped,
        y: pointer.y - mousePointTo.y * clamped,
      });
      onZoomApplied(clamped);
    },
    [stageRef, zoomDirection, onZoomApplied],
  );

  const doMarqueeZoom = useCallback(
    (x: number, y: number, w: number, h: number) => {
      const stage = stageRef.current;
      if (!stage) return;
      const rectWidth = Math.abs(w);
      const rectHeight = Math.abs(h);
      if (rectWidth < 2 || rectHeight < 2) return;

      const stageW = stage.width();
      const stageH = stage.height();
      const oldScale = stage.scaleX();

      let newScale: number;
      if (zoomDirection === "in") {
        // Fit the rectangle into the viewport
        newScale = Math.min(
          stageW / rectWidth,
          stageH / rectHeight,
        );
      } else {
        // Shrink viewport to fit inside the drawn rectangle
        newScale =
          oldScale *
          Math.min(rectWidth / stageW, rectHeight / stageH);
      }
      const clamped = Math.max(0.05, Math.min(newScale, 20));

      // Center the rectangle in the viewport
      const rectCenterX = x + w / 2;
      const rectCenterY = y + h / 2;
      stage.scale({ x: clamped, y: clamped });
      stage.position({
        x: stageW / 2 - rectCenterX * clamped,
        y: stageH / 2 - rectCenterY * clamped,
      });
      onZoomApplied(clamped);
    },
    [stageRef, zoomDirection, onZoomApplied],
  );

  // ── Finalization ──────────────────────────────────────────────────
  // Runs once per drag, from whichever of the Konva mouseup or the global
  // pointerup fires first. The global listener fires before Konva's mouseup,
  // so the finalization MUST live here (not only in onMouseUp) or it would
  // never run when the global listener resets the drag flag first.
  const finalizeZoom = useCallback(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const dx = marqueeWidthRef.current;
    const dy = marqueeHeightRef.current;
    if (Math.abs(dx) <= CLICK_THRESHOLD && Math.abs(dy) <= CLICK_THRESHOLD) {
      // Click zoom — zoom centered on the pointer
      const raw = stage.getPointerPosition();
      if (raw) doClickZoom(raw);
    } else {
      // Marquee zoom — use refs for synchronous access
      doMarqueeZoom(startPosRef.current.x, startPosRef.current.y, dx, dy);
    }
  }, [stageRef, doClickZoom, doMarqueeZoom]);

  // Own global pointerup listener — handles releases outside the Stage.
  useEffect(() => {
    const onGlobalUp = () => {
      if (!isActive || !dragStartedRef.current) return;
      dragStartedRef.current = false;
      setIsDrawing(false);
      finalizeZoom();
    };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup", onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup", onGlobalUp);
    };
  }, [isActive, finalizeZoom]);

  // ── Event handlers ────────────────────────────────────────────────

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;
      const pos = getCanvasPos();
      if (!pos) return false;
      startPosRef.current = { x: pos.x, y: pos.y };
      marqueeWidthRef.current = 0;
      marqueeHeightRef.current = 0;
      setMarqueeX(pos.x);
      setMarqueeY(pos.y);
      setMarqueeWidth(0);
      setMarqueeHeight(0);
      dragStartedRef.current = true;
      setIsDrawing(true);
      return true;
    },
    [isActive, getCanvasPos],
  );


  const onMouseMove = useCallback(
    (): boolean => {
      if (!isActive || !dragStartedRef.current) return false;
      const pos = getCanvasPos();
      if (!pos) return false;
      const dx = pos.x - startPosRef.current.x;
      const dy = pos.y - startPosRef.current.y;
      // Only treat as drag if movement exceeds threshold
      if (
        Math.abs(dx) > CLICK_THRESHOLD ||
        Math.abs(dy) > CLICK_THRESHOLD
      ) {
        marqueeWidthRef.current = dx;
        marqueeHeightRef.current = dy;
        setMarqueeWidth(dx);
        setMarqueeHeight(dy);
      }
      return true;
    },
    [isActive, getCanvasPos],
  );


  const onMouseUp = useCallback(
    (): boolean => {
      if (!isActive || !dragStartedRef.current) return false;
      dragStartedRef.current = false;
      setIsDrawing(false);
      finalizeZoom();
      return true;
    },
    [isActive, finalizeZoom],
  );

  return {
    renderState: {
      isDrawing,
      marqueeX,
      marqueeY,
      marqueeWidth,
      marqueeHeight,
    },
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
