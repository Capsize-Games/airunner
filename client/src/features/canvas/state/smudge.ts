// ── Smudge Tool Settings ───────────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function smudge({ setState }: CanvasSetters) {
  const setSmudgeSize = useCallback(
    (value: number) => {
      setState((prev) => ({
        ...prev,
        smudgeSize: Math.max(0, Math.min(100, value)),
      }));
    },
    [setState],
  );

  return { setSmudgeSize };
}
