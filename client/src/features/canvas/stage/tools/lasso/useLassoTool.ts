// ── Lasso (Free Select) Tool Hook ───────────────────────────────────────────
// Encapsulates all interaction state, refs, and mouse-event handlers for the
// lasso tool.  CanvasStage calls this hook and passes the returned
// { onMouseDown, onMouseMove, onMouseUp, renderState } to StageContent.
//
// Interaction model (mirrors GIMP's Free Select tool):
//   Click          → place a straight-line polygon vertex
//   Click + drag   → draw a freehand segment; release commits the endpoint
//   Click anchor   → drag that anchor to reshape the path (post-placement)
//   Click anchor 0 → (no drag) close the selection
//   Double-click   → close
//   Enter          → close / finalise
//   Escape         → reset / cancel

import { useState, useRef, useCallback, useEffect } from "react";
import Konva from "konva";

// ── Public types ─────────────────────────────────────────────────────────────

export interface LassoRenderState {
  /** Flat [x,y,...] array for the committed polygon/freehand path. */
  points: number[];
  /** Points being drawn during the current mouse-drag (cleared on mouseup). */
  freehandPoints: number[];
  /** Discrete anchor handles (one per commit point). */
  anchors: { x: number; y: number }[];
  /** Current cursor position — drives the rubber-band line. */
  cursorPos: { x: number; y: number } | null;
  /** Whether the selection has been closed. */
  isClosed: boolean;
}

export interface UseLassoToolReturn {
  renderState: LassoRenderState;
  /** Returns true if the event was consumed. */
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp:   (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

// ── Constants ────────────────────────────────────────────────────────────────

const CLOSE_THRESHOLD = 12; // px — click this close to anchor-0 to close
const DRAG_THRESHOLD  = 4;  // px — movement before a click becomes freehand
const HANDLE_RADIUS   = 8;  // px — hit-target size for anchor handles

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useLassoTool({
  isActive,
  getCanvasPos,
  stageRef,
}: {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
  stageRef: React.RefObject<Konva.Stage>;
}): UseLassoToolReturn {

  // ── React state (drives re-renders / rendering) ───────────────────────
  const [points,        setPoints]        = useState<number[]>([]);
  const [freehandPoints,setFreehandPoints] = useState<number[]>([]);
  const [anchors,       setAnchors]       = useState<{ x: number; y: number }[]>([]);
  const [cursorPos,     setCursorPos]     = useState<{ x: number; y: number } | null>(null);
  const [isClosed,      setIsClosed]      = useState(false);

  // ── Refs (synchronous cross-handler access, no re-render cost) ────────
  const anchorsRef      = useRef<{ x: number; y: number }[]>([]);
  const pointsRef       = useRef<number[]>([]);
  const freehandRef     = useRef<number[]>([]);
  const mouseDownRef    = useRef(false);
  const mouseDownPosRef = useRef<{ x: number; y: number } | null>(null);
  const isDraggingRef   = useRef(false);
  const justClosedRef   = useRef(false);
  const isClosedRef     = useRef(false); // sync mirror so global handler can read it

  // Anchor handle dragging
  const dragAnchorIdx   = useRef(-1);    // -1 = none
  const anchorDragging  = useRef(false);
  const closePendingRef = useRef(false); // click (not drag) on anchor-0 → close

  // ── Helpers ──────────────────────────────────────────────────────────

  const resetAll = useCallback(() => {
    setPoints([]);  setFreehandPoints([]); setAnchors([]);
    setCursorPos(null); setIsClosed(false);
    anchorsRef.current = []; pointsRef.current = []; freehandRef.current = [];
    mouseDownRef.current = false; isDraggingRef.current = false;
    justClosedRef.current = false; isClosedRef.current = false;
    dragAnchorIdx.current = -1; anchorDragging.current = false;
    closePendingRef.current = false;
  }, []);

  /** Commit the final position of the anchor being dragged, or close if it
   *  was a pure click on the first anchor. */
  const commitAnchorDrag = useCallback(
    (pos: { x: number; y: number } | null) => {
      if (pos && anchorDragging.current) {
        const idx = dragAnchorIdx.current;
        const updated = [...anchorsRef.current];
        updated[idx] = pos;
        anchorsRef.current = updated;
        const flat = updated.flatMap((a) => [a.x, a.y]);
        pointsRef.current = flat;
        setAnchors([...updated]);
        setPoints([...flat]);
      } else if (closePendingRef.current) {
        setIsClosed(true);
        isClosedRef.current = true;
      }
      dragAnchorIdx.current  = -1;
      anchorDragging.current = false;
      closePendingRef.current = false;
    },
    [],
  );

  /** Commit a polygon vertex (click) or freehand segment (drag) to the path. */
  const commitPoint = useCallback(
    (pos: { x: number; y: number }) => {
      const mdPos          = mouseDownPosRef.current;
      const currentAnchors = anchorsRef.current;

      if (isDraggingRef.current) {
        const freehandPts = freehandRef.current;
        let newPoints:  number[];
        let newAnchors: { x: number; y: number }[];

        if (currentAnchors.length === 0 && mdPos) {
          // First-ever action was a drag — freehandPts already starts at mdPos
          newPoints  = [...freehandPts, pos.x, pos.y];
          newAnchors = [mdPos, pos];
        } else {
          newPoints  = [...pointsRef.current, ...freehandPts, pos.x, pos.y];
          newAnchors = [...currentAnchors, pos];
        }

        pointsRef.current  = newPoints;
        anchorsRef.current = newAnchors;
        setPoints([...newPoints]);
        setAnchors([...newAnchors]);
        setFreehandPoints([]);
        freehandRef.current = [];
      } else {
        // Polygon click — straight line segment
        const newPoints  = currentAnchors.length === 0
          ? [pos.x, pos.y]
          : [...pointsRef.current, pos.x, pos.y];
        const newAnchors = currentAnchors.length === 0
          ? [pos]
          : [...currentAnchors, pos];

        pointsRef.current  = newPoints;
        anchorsRef.current = newAnchors;
        setPoints([...newPoints]);
        setAnchors([...newAnchors]);
      }

      isDraggingRef.current = false;
    },
    [],
  );

  // ── Side-effects ─────────────────────────────────────────────────────

  // Reset when the tool is deactivated
  useEffect(() => {
    if (!isActive) resetAll();
  }, [isActive, resetAll]);

  // Enter (close) / Escape (cancel) keys
  useEffect(() => {
    if (!isActive) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter" && anchorsRef.current.length >= 3) {
        setIsClosed(true);
        isClosedRef.current = true;
      }
      if (e.key === "Escape") resetAll();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isActive, resetAll]);

  // Global pointerup — handles releases outside the Stage
  useEffect(() => {
    const onGlobalUp = () => {
      if (!mouseDownRef.current) return; // Konva handler already processed this
      mouseDownRef.current = false;

      if (dragAnchorIdx.current >= 0) {
        commitAnchorDrag(getCanvasPos());
        return;
      }
      if (justClosedRef.current) { justClosedRef.current = false; return; }
      if (isClosedRef.current)   return;

      const pos = getCanvasPos();
      if (pos) commitPoint(pos);
    };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup",   onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup",   onGlobalUp);
    };
  }, [getCanvasPos, commitAnchorDrag, commitPoint]);

  // ── Event handlers ────────────────────────────────────────────────────

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;
      const pos = getCanvasPos();
      if (!pos) return true;

      // ── Anchor handle drag ──────────────────────────────────────────
      const nearIdx = anchorsRef.current.findIndex(
        (a) => Math.hypot(pos.x - a.x, pos.y - a.y) < HANDLE_RADIUS,
      );
      if (nearIdx >= 0) {
        dragAnchorIdx.current  = nearIdx;
        anchorDragging.current = false;
        mouseDownRef.current   = true;
        mouseDownPosRef.current = pos;
        // First anchor, non-drag click → should close (decided on mouseup)
        closePendingRef.current =
          !isClosedRef.current && nearIdx === 0 && anchorsRef.current.length >= 2;
        // NOTE: do not straighten the path here — that would discard freehand
        // points captured between anchors (e.g. when clicking anchor-0 to
        // close). Straightening only happens once an actual anchor drag begins
        // (see onMouseMove), which is the only case where it's intended.
        return true;
      }

      // Closed: ignore clicks outside handles
      if (isClosedRef.current) return true;

      // Double-click → close
      if (e.evt.detail === 2 && anchorsRef.current.length >= 2) {
        setIsClosed(true);
        isClosedRef.current  = true;
        justClosedRef.current = true;
        return true;
      }

      // Near first anchor → close
      if (anchorsRef.current.length >= 2) {
        const first = anchorsRef.current[0];
        if (Math.hypot(pos.x - first.x, pos.y - first.y) < CLOSE_THRESHOLD) {
          setIsClosed(true);
          isClosedRef.current  = true;
          justClosedRef.current = true;
          return true;
        }
      }

      // Normal: begin a new point / freehand segment
      justClosedRef.current  = false;
      mouseDownRef.current   = true;
      mouseDownPosRef.current = pos;
      isDraggingRef.current  = false;
      return true;
    },
    [isActive, getCanvasPos],
  );

  const onMouseMove = useCallback(
    (_e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive) return false;
      const pos = getCanvasPos();
      if (!pos) return true;
      setCursorPos(pos);

      const container = stageRef.current?.container();

      // ── Anchor handle drag in progress ──────────────────────────────
      if (dragAnchorIdx.current >= 0) {
        const mdPos = mouseDownPosRef.current;
        if (mdPos && !anchorDragging.current) {
          if (Math.hypot(pos.x - mdPos.x, pos.y - mdPos.y) > DRAG_THRESHOLD) {
            anchorDragging.current  = true;
            closePendingRef.current = false;
          }
        }
        if (anchorDragging.current) {
          const idx     = dragAnchorIdx.current;
          const updated = [...anchorsRef.current];
          updated[idx]  = pos;
          anchorsRef.current = updated;
          const flat = updated.flatMap((a) => [a.x, a.y]);
          pointsRef.current  = flat;
          setAnchors([...updated]);
          setPoints([...flat]);
        }
        if (container) container.style.cursor = "move";
        return true;
      }

      // ── Cursor shape: "move" when hovering a handle ─────────────────
      if (container) {
        const nearAny = anchorsRef.current.some(
          (a) => Math.hypot(pos.x - a.x, pos.y - a.y) < HANDLE_RADIUS,
        );
        container.style.cursor = nearAny ? "move" : "crosshair";
      }

      if (!mouseDownRef.current || isClosedRef.current) return true;
      const mdPos = mouseDownPosRef.current;
      if (!mdPos) return true;

      // ── Freehand drawing ─────────────────────────────────────────────
      if (!isDraggingRef.current) {
        if (Math.hypot(pos.x - mdPos.x, pos.y - mdPos.y) > DRAG_THRESHOLD) {
          isDraggingRef.current = true;
          const initPts = anchorsRef.current.length === 0
            ? [mdPos.x, mdPos.y, pos.x, pos.y]
            : [pos.x, pos.y];
          freehandRef.current = initPts;
          setFreehandPoints([...initPts]);
        }
        return true;
      }

      const next = [...freehandRef.current, pos.x, pos.y];
      freehandRef.current = next;
      setFreehandPoints([...next]);
      return true;
    },
    [isActive, getCanvasPos, stageRef],
  );

  const onMouseUp = useCallback(
    (_e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive) return false;
      if (!mouseDownRef.current) return false; // global handler already ran
      mouseDownRef.current = false;

      if (dragAnchorIdx.current >= 0) {
        commitAnchorDrag(getCanvasPos());
        return true;
      }

      if (justClosedRef.current) { justClosedRef.current = false; return true; }
      if (isClosedRef.current)   return true;

      const pos = getCanvasPos();
      if (pos) commitPoint(pos);
      return true;
    },
    [isActive, getCanvasPos, commitAnchorDrag, commitPoint],
  );

  // ── Return ────────────────────────────────────────────────────────────

  return {
    renderState: { points, freehandPoints, anchors, cursorPos, isClosed },
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
