// ── Fuzzy Select (Magic Wand) Tool Settings ──────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function wand({ setState }: CanvasSetters) {
  const setWandAntialiasing = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, wandAntialiasing: value }));
    },
    [setState],
  );

  const setWandFeatherEdges = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, wandFeatherEdges: value }));
    },
    [setState],
  );

  const setWandFeatherRadius = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        wandFeatherRadius: Math.max(0, Math.min(100, value)),
      }));
    },
    [setState],
  );

  const setWandSelectTransparentAreas = useCallback(
    (value: boolean) => {
      setState((prev) => ({
        ...prev,
        wandSelectTransparentAreas: value,
      }));
    },
    [setState],
  );

  const setWandSampleMerged = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, wandSampleMerged: value }));
    },
    [setState],
  );

  const setWandDiagonalNeighbors = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, wandDiagonalNeighbors: value }));
    },
    [setState],
  );

  const setWandThreshold = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        wandThreshold: Math.max(0, Math.min(100, value)),
      }));
    },
    [setState],
  );

  return {
    setWandAntialiasing,
    setWandFeatherEdges,
    setWandFeatherRadius,
    setWandSelectTransparentAreas,
    setWandSampleMerged,
    setWandDiagonalNeighbors,
    setWandThreshold,
  };
}
