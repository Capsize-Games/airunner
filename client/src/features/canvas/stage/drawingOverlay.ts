// ── Canvas Drawing Overlay Hook ─────────────────────────────────────────
// Brush/eraser drawing handlers, brush indicator, live stroke sync.

import {
  useCallback,
  useEffect,
  useRef,
  useMemo,
} from "react";
import Konva from "konva";
import type {
  CanvasLayer,
  ActiveTool,
  StrokeNode,
} from "../useCanvasState";
import type {
  LiveStrokeMessage,
  StrokeEndMessage,
} from "../canvasSyncTypes";
import { getCursor } from "../cursorUtils";
import {
  lerp,
  clampToDoc,
  getCanvasPosFromStage,
  INTERP_THRESHOLD,
} from "./drawingHelpers";

interface Params {
  stageRef: React.RefObject<Konva.Stage>;
  layers: CanvasLayer[];
  activeLayerId: string | null;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  documentWidth: number;
  documentHeight: number;
  zoom: number;
  onAddStroke: (
    stroke: Omit<StrokeNode, "id">,
  ) => void;
  sendLiveStroke?: (msg: LiveStrokeMessage) => void;
  sendStrokeEnd?: (msg: StrokeEndMessage) => void;
}

/** Accessor for the global live-stroke Line ref set by DrawingLayer. */
function getLiveStroke(): Konva.Line | null {
  return (
    window as unknown as Record<
      string,
      Konva.Line | undefined
    >
  ).__airunnerLiveStrokeRef ?? null;
}

export function drawingOverlay({
  stageRef,
  layers,
  activeLayerId,
  activeTool,
  brushSize,
  brushColor,
  documentWidth,
  documentHeight,
  zoom,
  onAddStroke,
  sendLiveStroke,
  sendStrokeEnd,
}: Params) {
  // ── Session identity (stable for tab lifetime) ────────────────────────
  const sessionId = useRef(crypto.randomUUID());

  // ── Drawing state (mutable refs, not React state) ─────────────────────
  const isDrawingOverlay = useRef(false);
  const drawingPoints = useRef<number[]>([]);
  const liveStrokeId = useRef("");
  const lastSentCount = useRef(0);
  const liveThrottleRef = useRef<ReturnType<
    typeof setTimeout
  > | null>(null);

  // ── Brush indicator Konva refs ────────────────────────────────────────
  const brushRingRef = useRef<Konva.Circle | null>(null);
  const brushDotRef = useRef<Konva.Circle | null>(null);
  const brushIndicatorLayerRef =
    useRef<Konva.Layer | null>(null);

  const isDrawingTool =
    activeTool === "brush" || activeTool === "eraser";
  const showBrushIndicator =
    isDrawingTool || activeTool === "mask";
  const brushRadius = (brushSize * zoom) / 2;
  const indicatorColor =
    activeTool === "eraser"
      ? "rgba(200,200,200,0.8)"
      : activeTool === "mask"
        ? "rgba(255,255,255,0.8)"
        : brushColor;

  // ── Derived ───────────────────────────────────────────────────────────
  const activeLayer = useMemo(
    () =>
      layers.find((l) => l.id === activeLayerId) ?? null,
    [layers, activeLayerId],
  );
  const drawingOffsetX = activeLayer?.offsetX ?? 0;
  const drawingOffsetY = activeLayer?.offsetY ?? 0;

  // ── Imperative brush indicator update ─────────────────────────────────
  const updateBrushIndicator = useCallback(
    (pos: { x: number; y: number } | null) => {
      const ring = brushRingRef.current;
      const dot = brushDotRef.current;
      if (!ring || !dot) return;
      if (pos) {
        ring.position(pos);
        dot.position(pos);
        ring.visible(true);
        dot.visible(true);
      } else {
        ring.visible(false);
        dot.visible(false);
      }
    },
    [],
  );

  // Konva native mousemove for smooth brush indicator
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const handler = () => {
      const raw = stage.getPointerPosition();
      if (!raw) return;
      const doc = stage
        .getAbsoluteTransform()
        .copy()
        .invert()
        .point(raw);
      updateBrushIndicator(doc);
    };
    stage.on("mousemove", handler);
    return () => {
      stage.off("mousemove", handler);
    };
  }, [updateBrushIndicator]);

  // Cursor update when tool or layer count changes
  useEffect(() => {
    const container = stageRef.current?.container();
    if (container) {
      container.style.cursor = getCursor(
        activeTool,
        layers.length > 0,
      );
    }
  }, [activeTool, layers.length, stageRef]);

  // Clear selection when switching away from select tool
  useEffect(() => {
    // handled by parent via setSelectionRect(null)
  }, [activeTool]);

  // ── Drawing overlay pointer handlers ──────────────────────────────────
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const handleOverlayPointerDown = useCallback(
    (e: Konva.KonvaEventObject<PointerEvent>) => {
      if (e.evt.button !== 0) return;
      if (!activeLayerId || !isDrawingTool) return;
      const pos = getCanvasPosFromStage(stageRef.current);
      if (!pos) return;
      const local = {
        x: pos.x - drawingOffsetX,
        y: pos.y - drawingOffsetY,
      };
      const clamped = clampToDoc(
        local.x,
        local.y,
        documentWidth,
        documentHeight,
        0,
        drawingOffsetX,
        drawingOffsetY,
      );
      isDrawingOverlay.current = true;
      drawingPoints.current = [clamped.x, clamped.y];
      liveStrokeId.current = crypto.randomUUID();
      lastSentCount.current = 0;
      const liveStroke = getLiveStroke();
      if (liveStroke) {
        liveStroke.points([clamped.x, clamped.y]);
        liveStroke.getLayer()?.batchDraw();
      }
    },
    [
      activeLayerId,
      isDrawingTool,
      documentWidth,
      documentHeight,
      drawingOffsetX,
      drawingOffsetY,
    ],
  );

  const handleOverlayPointerMove = useCallback(
    () => {
      if (!isDrawingOverlay.current) return;
      const pos = getCanvasPosFromStage(
        stageRef.current,
      );
      if (!pos) return;
      const local = {
        x: pos.x - drawingOffsetX,
        y: pos.y - drawingOffsetY,
      };
      const clamped = clampToDoc(
        local.x,
        local.y,
        documentWidth,
        documentHeight,
        0,
        drawingOffsetX,
        drawingOffsetY,
      );
      const pts = drawingPoints.current;
      if (pts.length >= 2) {
        const px = pts[pts.length - 2];
        const py = pts[pts.length - 1];
        const dx = clamped.x - px;
        const dy = clamped.y - py;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > INTERP_THRESHOLD) {
          const steps = Math.floor(
            dist / INTERP_THRESHOLD,
          );
          for (let i = 1; i <= steps; i++) {
            const t = i / (steps + 1);
            const ip = lerp(
              px,
              py,
              clamped.x,
              clamped.y,
              t,
            );
            pts.push(ip.x, ip.y);
          }
        }
      }
      pts.push(clamped.x, clamped.y);
      const liveStroke2 = getLiveStroke();
      if (liveStroke2) {
        liveStroke2.points([...pts]);
        liveStroke2.getLayer()?.batchDraw();
      }

      // Throttled live-stroke delta send (80 ms)
      if (
        !liveThrottleRef.current &&
        sendLiveStroke &&
        activeLayerId
      ) {
        liveThrottleRef.current = setTimeout(() => {
          liveThrottleRef.current = null;
          const currentPts = drawingPoints.current;
          const delta = currentPts.slice(
            lastSentCount.current,
          );
          if (delta.length > 0) {
            lastSentCount.current = currentPts.length;
            sendLiveStroke({
              type: "stroke:live",
              sessionId: sessionId.current,
              layerId: activeLayerId,
              strokeId: liveStrokeId.current,
              tool: activeTool as "brush" | "eraser",
              color: brushColor,
              strokeWidth: brushSize,
              delta,
            });
          }
        }, 80);
      }
    },
    [
      brushSize,
      documentWidth,
      documentHeight,
      drawingOffsetX,
      drawingOffsetY,
      sendLiveStroke,
      activeLayerId,
      activeTool,
      brushColor,
    ],
  );

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const handleOverlayPointerUp = useCallback(() => {
    if (!isDrawingOverlay.current) return;
    isDrawingOverlay.current = false;

    if (liveThrottleRef.current) {
      clearTimeout(liveThrottleRef.current);
      liveThrottleRef.current = null;
    }

    if (sendStrokeEnd) {
      sendStrokeEnd({
        type: "stroke:end",
        sessionId: sessionId.current,
        strokeId: liveStrokeId.current,
      });
    }
    lastSentCount.current = 0;

    const liveStroke3 = getLiveStroke();
    if (liveStroke3) {
      liveStroke3.points([]);
      liveStroke3.getLayer()?.batchDraw();
    }
    if (drawingPoints.current.length < 4) {
      drawingPoints.current = [];
      return;
    }
    onAddStroke({
      points: [...drawingPoints.current],
      color:
        activeTool === "eraser" ? "#000000" : brushColor,
      strokeWidth: brushSize,
      tool: activeTool as "brush" | "eraser",
    });
    drawingPoints.current = [];
  }, [
    activeTool,
    brushSize,
    brushColor,
    onAddStroke,
    sendStrokeEnd,
  ]);

  // Catch pointerup anywhere in the browser window
  useEffect(() => {
    window.addEventListener(
      "pointerup",
      handleOverlayPointerUp,
    );
    return () =>
      window.removeEventListener(
        "pointerup",
        handleOverlayPointerUp,
      );
  }, [handleOverlayPointerUp]);

  return {
    isDrawingOverlay,
    isDrawingTool,
    drawingOffsetX,
    drawingOffsetY,
    showBrushIndicator,
    brushRadius,
    indicatorColor,
    brushRingRef,
    brushDotRef,
    brushIndicatorLayerRef,
    handleOverlayPointerDown,
    handleOverlayPointerMove,
    handleOverlayPointerUp,
    updateBrushIndicator,
  };
}
