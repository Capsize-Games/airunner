// ── Canvas Brush Controls ───────────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function brush(
  { setState }: CanvasSetters,
) {
  const setBrushSize = useCallback(
    (size: number) => {
      setState((prev) => ({
        ...prev,
        brushSize: Math.max(1, size),
      }));
    },
    [setState],
  );

  const setBrushColor = useCallback(
    (color: string) => {
      setState((prev) => ({ ...prev, brushColor: color }));
    },
    [setState],
  );

  return { setBrushSize, setBrushColor };
}
