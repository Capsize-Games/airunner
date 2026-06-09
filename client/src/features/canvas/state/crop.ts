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
        cropWidth: Math.max(1, Math.round(value)),
      }));
    },
    [setState],
  );

  const setCropHeight = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        cropHeight: Math.max(1, Math.round(value)),
      }));
    },
    [setState],
  );

  return { setCropX, setCropY, setCropWidth, setCropHeight };
}
