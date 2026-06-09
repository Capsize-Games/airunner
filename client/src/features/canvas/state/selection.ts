// ── Canvas Selection Operations ─────────────────────────────────────────
import { useCallback } from "react";
import type { ImageNode, StrokeNode } from "../canvasTypes";
import type { CanvasSetters } from "./types";

export function selection(
  { setState, recordSnapshot }: CanvasSetters,
) {
  const setActiveLayer = useCallback(
    (id: string) => {
      setState((prev) => ({
        ...prev,
        activeLayerId: id,
        selectedLayerIds: [id],
      }));
    },
    [setState],
  );

  const toggleLayerSelection = useCallback(
    (id: string) => {
      setState((prev) => {
        const isSelected = prev.selectedLayerIds.includes(id);
        const nextSelection = isSelected
          ? prev.selectedLayerIds.filter((s) => s !== id)
          : [...prev.selectedLayerIds, id];
        if (nextSelection.length === 0) return prev;
        return { ...prev, selectedLayerIds: nextSelection };
      });
    },
    [setState],
  );

  const selectLayerRange = useCallback(
    (id: string) => {
      setState((prev) => {
        const startIdx = prev.layers.findIndex(
          (l) => l.id === prev.activeLayerId,
        );
        const endIdx = prev.layers.findIndex(
          (l) => l.id === id,
        );
        if (startIdx === -1 || endIdx === -1) return prev;
        const lo = Math.min(startIdx, endIdx);
        const hi = Math.max(startIdx, endIdx);
        const rangeIds = prev.layers
          .slice(lo, hi + 1)
          .map((l) => l.id);
        return {
          ...prev,
          selectedLayerIds: rangeIds,
          activeLayerId: id,
        };
      });
    },
    [setState],
  );

  const reorderLayerToIndex = useCallback(
    (id: string, toIndex: number) => {
      setState((prev) => {
        const fromIdx = prev.layers.findIndex(
          (l) => l.id === id,
        );
        if (fromIdx === -1 || fromIdx === toIndex) return prev;
        const layers = [...prev.layers];
        const [moved] = layers.splice(fromIdx, 1);
        const adjusted =
          toIndex > fromIdx ? toIndex - 1 : toIndex;
        layers.splice(adjusted, 0, moved);
        return recordSnapshot({ ...prev, layers });
      });
    },
    [setState, recordSnapshot],
  );

  const mergeSelectedLayers = useCallback(() => {
    setState((prev) => {
      const sel = prev.selectedLayerIds;
      if (sel.length < 1) return prev;

      const sorted = [...sel]
        .map((id) => ({
          id,
          idx: prev.layers.findIndex((l) => l.id === id),
        }))
        .filter((e) => e.idx !== -1)
        .sort((a, b) => a.idx - b.idx);

      if (sorted.length === 0) return prev;

      const targetIdx = sorted[0].idx - 1;
      if (targetIdx < 0) return prev;

      const targetId = prev.layers[targetIdx].id;
      const mergeIds = new Set(sorted.map((e) => e.id));

      const extraImages: ImageNode[] = [];
      const extraStrokes: StrokeNode[] = [];
      for (const { id } of sorted) {
        const mLayer = prev.layers.find((l) => l.id === id);
        if (!mLayer) continue;
        extraImages.push(...mLayer.images);
        extraStrokes.push(...mLayer.strokes);
      }

      const mergedLayers = prev.layers
        .filter((l) => !mergeIds.has(l.id))
        .map((l) =>
          l.id === targetId
            ? {
                ...l,
                images: [...l.images, ...extraImages],
                strokes: [...l.strokes, ...extraStrokes],
              }
            : l,
        );

      return recordSnapshot({
        ...prev,
        layers: mergedLayers,
        selectedLayerIds: [targetId],
        activeLayerId: targetId,
      });
    });
  }, [setState, recordSnapshot]);

  return {
    setActiveLayer,
    toggleLayerSelection,
    selectLayerRange,
    reorderLayerToIndex,
    mergeSelectedLayers,
  };
}
