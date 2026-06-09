// ── Text Tool Settings ────────────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasSetters } from "./types";
import type { TextNodeData } from "../canvasTypes";

export function text({ setState }: CanvasSetters) {
  const setTextFont = useCallback(
    (value: string) => setState((prev) => ({ ...prev, textFont: value })),
    [setState],
  );
  const setTextSize = useCallback(
    (value: number) =>
      setState((prev) => ({
        ...prev,
        textSize: Math.max(1, Math.min(512, value)),
      })),
    [setState],
  );
  const setTextColor = useCallback(
    (value: string) => setState((prev) => ({ ...prev, textColor: value })),
    [setState],
  );

  const setTextNode = useCallback(
    (layerId: string, textNode: TextNodeData) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map((l) =>
          l.id === layerId ? { ...l, textNode } : l,
        ),
      }));
    },
    [setState],
  );

  return { setTextFont, setTextSize, setTextColor, setTextNode };
}
