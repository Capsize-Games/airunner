// ── Grid Tool Settings ─────────────────────────────────────────────
/* eslint-disable react-hooks/rules-of-hooks */
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function grid({ setState }: CanvasSetters) {
  const setGridShowGrid = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, gridShowGrid: value }));
    },
    [setState],
  );

  const setGridSize = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        gridSize: Math.max(8, Math.min(512, value)),
      }));
    },
    [setState],
  );

  const setGridColor = useCallback(
    (value: string) => {
      setState((prev) => ({ ...prev, gridColor: value }));
    },
    [setState],
  );

  return { setGridShowGrid, setGridSize, setGridColor };
}
