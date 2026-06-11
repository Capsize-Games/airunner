// ── Active Selection Operations ─────────────────────────────────────────
// The committed, tool-independent document-space selection. Set by the
// selection tools, cleared by "Select None", and set to the whole document
// by "Select All". Persists across tool switches and reloads.
import { useCallback } from "react";
import type { SelectionData } from "../canvasTypes";
import type { CanvasSetters } from "./types";

function boundsOf(points: number[]): SelectionData["bounds"] {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let i = 0; i < points.length; i += 2) {
    const x = points[i];
    const y = points[i + 1];
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  }
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

export function selectionMask({ setState }: CanvasSetters) {
  /** Replace the active selection with a polygon (flat document-space points). */
  const setSelection = useCallback(
    (points: number[], feather = 0, antialias = true) => {
      setState((prev) => {
        if (points.length < 6) return { ...prev, selection: null };
        return {
          ...prev,
          selection: { points, bounds: boundsOf(points), feather, antialias },
        };
      });
    },
    [setState],
  );

  /** Deselect everything (Select → None). */
  const clearSelection = useCallback(() => {
    setState((prev) =>
      prev.selection === null ? prev : { ...prev, selection: null },
    );
  }, [setState]);

  /** Select the whole document (Select → All). */
  const selectAll = useCallback(() => {
    setState((prev) => {
      const w = prev.documentWidth;
      const h = prev.documentHeight;
      const points = [0, 0, w, 0, w, h, 0, h];
      return {
        ...prev,
        selection: {
          points,
          bounds: { x: 0, y: 0, width: w, height: h },
          feather: 0,
          antialias: true,
        },
      };
    });
  }, [setState]);

  return { setSelection, clearSelection, selectAll };
}
