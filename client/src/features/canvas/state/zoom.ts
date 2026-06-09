// ── Zoom Tool Settings ─────────────────────────────────────────────
/* eslint-disable react-hooks/rules-of-hooks */
import { useCallback } from "react";
import type { CanvasSetters } from "./types";
import type { ZoomDirection } from "../canvasTypes";

export function zoom({ setState }: CanvasSetters) {
  const setZoomDirection = useCallback(
    (value: ZoomDirection) => {
      setState((prev) => ({ ...prev, zoomDirection: value }));
    },
    [setState],
  );

  return { setZoomDirection };
}
