// ── Pipette (Color Picker) Tool Settings ──────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function pipette({ setState }: CanvasSetters) {
  const setPipetteTarget = useCallback(
    (value: "foreground" | "background") => {
      setState((prev) => ({ ...prev, pipetteTarget: value }));
    },
    [setState],
  );

  return { setPipetteTarget };
}
