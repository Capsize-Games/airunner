// ── Ruler Tool Settings ───────────────────────────────────────────
/* eslint-disable react-hooks/rules-of-hooks */
import { useCallback } from "react";
import type { CanvasSetters } from "./types";

export function ruler({ setState }: CanvasSetters) {
  const setRulerShowRuler = useCallback(
    (value: boolean) => {
      setState((prev) => ({ ...prev, rulerShowRuler: value }));
    },
    [setState],
  );

  return { setRulerShowRuler };
}
