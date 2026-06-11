// ── Crop Tool Settings ──────────────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function crop({ setState }: CanvasSetters) {
  const setCropX = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        cropX: Math.max(0, Math.round(value)),
      }));
    },
    [setState],
  );

  const setCropY = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        cropY: Math.max(0, Math.round(value)),
      }));
    },
    [setState],
  );

  const setCropWidth = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        // 0 means "no crop drawn yet"; otherwise round to a whole pixel.
        cropWidth: Math.max(0, Math.round(value)),
      }));
    },
    [setState],
  );

  const setCropHeight = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        cropHeight: Math.max(0, Math.round(value)),
      }));
    },
    [setState],
  );

  return { setCropX, setCropY, setCropWidth, setCropHeight };
}
