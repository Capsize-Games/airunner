// ── Bucket (Flood) Fill Tool Settings ─────────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function bucket({ setState }: CanvasSetters) {
  const setBucketColorSource = useCallback(
    (value: "foreground" | "background") => {
      setState((prev) => ({ ...prev, bucketColorSource: value }));
    },
    [setState],
  );

  const setBucketFillTransparentAreas = useCallback(
    (value: boolean) => {
      setState((prev) => ({
        ...prev,
        bucketFillTransparentAreas: value,
      }));
    },
    [setState],
  );

  const setBucketAntialiasing = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, bucketAntialiasing: value }));
    },
    [setState],
  );

  const setBucketThreshold = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        bucketThreshold: Math.max(0, Math.min(100, value)),
      }));
    },
    [setState],
  );

  return {
    setBucketColorSource,
    setBucketFillTransparentAreas,
    setBucketAntialiasing,
    setBucketThreshold,
  };
}
