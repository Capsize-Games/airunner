// ── Rectangular Select Tool Hook ─────────────────────────────────────────────
// Encapsulates interaction state and mouse handlers for the marquee selection
// rectangle tool.  CanvasStage calls this hook and passes the returned
// { onMouseDown, onMouseMove, onMouseUp, renderState } to StageContent.

import { useState, useRef, useCallback, useEffect } from "react";
import Konva from "konva";

// ── Public types ─────────────────────────────────────────────────────────────

export interface SelectRenderState {
  /** The current selection rectangle, or null when no selection is active. */
  rect: { x: number; y: number; width: number; height: number } | null;
}

export interface UseSelectToolReturn {
  renderState: SelectRenderState;
  /** Returns true if the event was consumed. */
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp:   (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useSelectTool({
  isActive,
  getCanvasPos,
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
}): UseSelectToolReturn {

  const [rect, setRect] = useState<SelectRenderState["rect"]>(null);
  const startRef = useRef<{ x: number; y: number } | null>(null);

  // Clear when tool is deactivated
  useEffect(() => {
    if (!isActive) {
      setRect(null);
      startRef.current = null;
    }
  }, [isActive]);

  // Global up — catches releases outside the Stage
  useEffect(() => {
    const onGlobalUp = () => { startRef.current = null; };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup",   onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup",   onGlobalUp);
    };
  }, []);

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;
      const pos = getCanvasPos();
      if (!pos) return true;
      startRef.current = pos;
      setRect({ x: pos.x, y: pos.y, width: 0, height: 0 });
      return true;
    },
    [isActive, getCanvasPos],
  );

  const onMouseMove = useCallback(
    (_e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive) return false;
      if (!startRef.current) return true; // active, nothing to update
      const pos = getCanvasPos();
      if (!pos) return true;
      const sx = startRef.current.x;
      const sy = startRef.current.y;
      setRect({
        x: Math.min(sx, pos.x),
        y: Math.min(sy, pos.y),
        width:  Math.abs(pos.x - sx),
        height: Math.abs(pos.y - sy),
      });
      return true;
    },
    [isActive, getCanvasPos],
  );

  const onMouseUp = useCallback(
    (_e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive) return false;
      startRef.current = null;
      return true;
    },
    [isActive],
  );

  return {
    renderState: { rect },
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
