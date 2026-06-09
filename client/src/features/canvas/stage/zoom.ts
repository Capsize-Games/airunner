// ── Canvas Stage Zoom Hook ──────────────────────────────────────────────
// Zoom state, ResizeObserver, imperative handle, wheel zoom, multi-touch.

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useImperativeHandle,
  useState,
  useRef,
} from "react";
import Konva from "konva";
import type { CanvasStageHandle } from "./types";

interface Params {
  stageRef: React.RefObject<Konva.Stage>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  documentWidth: number;
  documentHeight: number;
  onZoomChange: (zoom: number) => void;
  zoomMode: "fit" | "locked";
  onZoomModeChange: (mode: "fit" | "locked") => void;
  handleRef: React.ForwardedRef<CanvasStageHandle>;
}

const PADDING = 40;

export function zoom({
  stageRef,
  containerRef,
  documentWidth,
  documentHeight,
  onZoomChange,
  zoomMode,
  onZoomModeChange,
  handleRef,
}: Params) {
  const [zoom, setZoom] = useState(1);
  const [stageSize, setStageSize] = useState({ width: 800, height: 600 });
  const zoomModeRef = useRef(zoomMode);
  const onZoomModeChangeRef = useRef(onZoomModeChange);
  const lastPointerPos = useRef({ x: 0, y: 0 });
  const lastTouchDist = useRef(0);

  useEffect(() => {
    zoomModeRef.current = zoomMode;
  }, [zoomMode]);
  useEffect(() => {
    onZoomModeChangeRef.current = onZoomModeChange;
  }, [onZoomModeChange]);

  // ── Fit on first mount + ResizeObserver ───────────────────────────────
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setStageSize({ width, height });
      const stage = stageRef.current;
      if (!stage) return;
      if (zoomModeRef.current === "fit") {
        const fitScale = Math.min(
          (width - PADDING) / Math.max(documentWidth, 1),
          (height - PADDING) / Math.max(documentHeight, 1),
          1,
        );
        stage.scale({ x: fitScale, y: fitScale });
        setZoom(fitScale);
        onZoomChange(fitScale);
        stage.position({
          x: (width - documentWidth * fitScale) / 2,
          y: (height - documentHeight * fitScale) / 2,
        });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [stageRef, documentWidth, documentHeight, onZoomChange]);

  // ── Imperative handle ─────────────────────────────────────────────────
  useImperativeHandle(
    handleRef,
    () => ({
      zoomIn: () => {
        const stage = stageRef.current;
        if (!stage) return;
        const newScale = Math.min(
          stage.scaleX() * 1.25,
          20,
        );
        stage.scale({ x: newScale, y: newScale });
        setZoom(newScale);
        onZoomChange(newScale);
        onZoomModeChange("locked");
      },
      zoomOut: () => {
        const stage = stageRef.current;
        if (!stage) return;
        const newScale = Math.max(
          stage.scaleX() / 1.25,
          0.05,
        );
        stage.scale({ x: newScale, y: newScale });
        setZoom(newScale);
        onZoomChange(newScale);
        onZoomModeChange("locked");
      },
      zoomReset: () => {
        const stage = stageRef.current;
        const container = containerRef.current;
        if (!stage) return;
        stage.scale({ x: 1, y: 1 });
        stage.position({
          x: container
            ? (container.clientWidth - documentWidth) / 2
            : 0,
          y: container
            ? (container.clientHeight - documentHeight) /
                2
            : 0,
        });
        setZoom(1);
        onZoomChange(1);
        onZoomModeChange("locked");
      },
      centerView: () => {
        const stage = stageRef.current;
        const container = containerRef.current;
        if (!stage || !container) return;
        const scale = stage.scaleX();
        stage.position({
          x:
            (container.clientWidth -
              documentWidth * scale) /
            2,
          y:
            (container.clientHeight -
              documentHeight * scale) /
            2,
        });
      },
      fitView: () => {
        const stage = stageRef.current;
        const container = containerRef.current;
        if (!stage || !container) return;
        const width = container.clientWidth;
        const height = container.clientHeight;
        const fitScale = Math.min(
          (width - PADDING) / Math.max(documentWidth, 1),
          (height - PADDING) / Math.max(documentHeight, 1),
          1,
        );
        stage.scale({ x: fitScale, y: fitScale });
        stage.position({
          x:
            (width - documentWidth * fitScale) / 2,
          y:
            (height - documentHeight * fitScale) / 2,
        });
        setZoom(fitScale);
        onZoomChange(fitScale);
        onZoomModeChange("fit");
      },
      getZoom: () => stageRef.current?.scaleX() ?? 1,
      getStage: () => stageRef.current,
    }),
    [
      stageRef,
      documentWidth,
      documentHeight,
      onZoomChange,
      onZoomModeChange,
    ],
  );

  // ── Wheel zoom ────────────────────────────────────────────────────────
  const handleWheel = useCallback(
    (e: Konva.KonvaEventObject<WheelEvent>) => {
      e.evt.preventDefault();
      const stage = stageRef.current;
      if (!stage) return;
      const scaleBy = 1.08;
      const oldScale = stage.scaleX();
      const pointer = stage.getPointerPosition();
      if (!pointer) return;
      const newScale =
        e.evt.deltaY < 0
          ? oldScale * scaleBy
          : oldScale / scaleBy;
      const clampedScale = Math.max(
        0.05,
        Math.min(newScale, 20),
      );
      const mousePointTo = {
        x: (pointer.x - stage.x()) / oldScale,
        y: (pointer.y - stage.y()) / oldScale,
      };
      stage.scale({ x: clampedScale, y: clampedScale });
      stage.position({
        x: pointer.x - mousePointTo.x * clampedScale,
        y: pointer.y - mousePointTo.y * clampedScale,
      });
      setZoom(clampedScale);
      onZoomChange(clampedScale);
      onZoomModeChangeRef.current("locked");
    },
    [stageRef, onZoomChange],
  );

  // ── Multi-touch pinch/pan ─────────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const onStart = (e: TouchEvent) => {
      if (e.touches.length < 2) return;
      e.preventDefault();
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      lastPointerPos.current = {
        x: (t1.clientX + t2.clientX) / 2,
        y: (t1.clientY + t2.clientY) / 2,
      };
      lastTouchDist.current = Math.hypot(
        t1.clientX - t2.clientX,
        t1.clientY - t2.clientY,
      );
    };
    const onMove = (e: TouchEvent) => {
      if (e.touches.length < 2) return;
      e.preventDefault();
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const mx = (t1.clientX + t2.clientX) / 2;
      const my = (t1.clientY + t2.clientY) / 2;
      const dx = mx - lastPointerPos.current.x;
      const dy = my - lastPointerPos.current.y;
      lastPointerPos.current = { x: mx, y: my };
      const dist = Math.hypot(
        t1.clientX - t2.clientX,
        t1.clientY - t2.clientY,
      );
      const stage = stageRef.current;
      if (!stage) return;
      if (lastTouchDist.current > 0) {
        const pinchRatio = dist / lastTouchDist.current;
        if (Math.abs(pinchRatio - 1) > 0.03) {
          const newScale = Math.max(
            0.05,
            Math.min(
              stage.scaleX() * pinchRatio,
              20,
            ),
          );
          stage.scale({ x: newScale, y: newScale });
          setZoom(newScale);
          onZoomChange(newScale);
          onZoomModeChangeRef.current("locked");
          lastTouchDist.current = dist;
        }
      }
      stage.position({
        x: stage.x() + dx,
        y: stage.y() + dy,
      });
      lastTouchDist.current = dist;
    };
    const onEnd = () => {
      lastTouchDist.current = 0;
    };
    container.addEventListener("touchstart", onStart, {
      passive: false,
    });
    container.addEventListener("touchmove", onMove, {
      passive: false,
    });
    container.addEventListener("touchend", onEnd);
    return () => {
      container.removeEventListener("touchstart", onStart);
      container.removeEventListener("touchmove", onMove);
      container.removeEventListener("touchend", onEnd);
    };
  }, [stageRef, onZoomChange]);

  return { zoom, setZoom, stageSize, handleWheel };
}
