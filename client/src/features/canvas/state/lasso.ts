// ── Lasso Tool Settings ──────────────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function lasso({ setState }: CanvasSetters) {
  const setLassoAntialiasing = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, lassoAntialiasing: value }));
    },
    [setState],
  );

  const setLassoFeatherEdges = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, lassoFeatherEdges: value }));
    },
    [setState],
  );

  const setLassoFeatherRadius = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        lassoFeatherRadius: Math.max(0, Math.min(100, value)),
      }));
    },
    [setState],
  );

  return { setLassoAntialiasing, setLassoFeatherEdges, setLassoFeatherRadius };
}
