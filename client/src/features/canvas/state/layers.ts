// ── Canvas Layer Operations ─────────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasLayer } from "../canvasTypes";
import { nextLayerId } from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

export function layers(
  { setState, recordSnapshot }: CanvasSetters,
) {
  const addLayer = useCallback(
    (name?: string, opacity?: number) => {
      setState((prev) => {
        const newLayer: CanvasLayer = {
          id: nextLayerId(),
          name: name || `Layer ${prev.layers.length + 1}`,
          visible: true,
          opacity: opacity ?? 1,
          filters: [],
          images: [],
          strokes: [],
          offsetX: 0,
          offsetY: 0,
          parentGroupId: null,
          fillColor: undefined,
        };
        return recordSnapshot({
          ...prev,
          layers: [...prev.layers, newLayer],
          displayOrder: [...prev.displayOrder, newLayer.id],
          activeLayerId: newLayer.id,
          selectedLayerIds: [newLayer.id],
        });
      });
    },
    [setState, recordSnapshot],
  );

  const deleteLayer = useCallback(
    (id: string) => {
      setState((prev) => {
        const filtered = prev.layers.filter((l) => l.id !== id);
        let newActive = prev.activeLayerId;
        if (newActive === id) {
          newActive = filtered.at(-1)?.id ?? null;
        }
        const cleanedSelection = prev.selectedLayerIds.filter(
          (s) => s !== id,
        );
        return recordSnapshot({
          ...prev,
          layers: filtered,
          displayOrder: prev.displayOrder.filter(
            (oid) => oid !== id,
          ),
          activeLayerId: newActive,
          selectedLayerIds:
            cleanedSelection.length > 0
              ? cleanedSelection
              : newActive
                ? [newActive]
                : [],
        });
      });
    },
    [setState, recordSnapshot],
  );

  const renameLayer = useCallback(
    (id: string, name: string) => {
      setState((prev) =>
        recordSnapshot({
          ...prev,
          layers: prev.layers.map((l) =>
            l.id === id ? { ...l, name } : l,
          ),
        }),
      );
    },
    [setState, recordSnapshot],
  );

  const setLayerVisible = useCallback(
    (id: string, visible: boolean) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map((l) =>
          l.id === id ? { ...l, visible } : l,
        ),
      }));
    },
    [setState],
  );

  const setLayerOpacity = useCallback(
    (id: string, opacity: number) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map((l) =>
          l.id === id ? { ...l, opacity } : l,
        ),
      }));
    },
    [setState],
  );

  const reorderLayer = useCallback(
    (id: string, direction: "up" | "down") => {
      setState((prev) => {
        const idx = prev.layers.findIndex((l) => l.id === id);
        if (idx === -1) return prev;
        const otherIdx =
          direction === "up" ? idx + 1 : idx - 1;
        if (
          (direction === "up" &&
            idx >= prev.layers.length - 1) ||
          (direction === "down" && idx <= 0)
        ) {
          return prev;
        }
        const layers = [...prev.layers];
        [layers[idx], layers[otherIdx]] = [
          layers[otherIdx],
          layers[idx],
        ];
        // Keep displayOrder in sync.
        const a = prev.layers[idx];
        const b = prev.layers[otherIdx];
        let displayOrder = prev.displayOrder;
        if (!a.parentGroupId && !b.parentGroupId) {
          const diA = displayOrder.indexOf(a.id);
          const diB = displayOrder.indexOf(b.id);
          if (diA !== -1 && diB !== -1 && diA !== diB) {
            displayOrder = [...displayOrder];
            [displayOrder[diA], displayOrder[diB]] = [
              displayOrder[diB],
              displayOrder[diA],
            ];
          }
        }
        return recordSnapshot({
          ...prev,
          layers,
          displayOrder,
        });
      });
    },
    [setState, recordSnapshot],
  );

  return {
    addLayer,
    deleteLayer,
    renameLayer,
    setLayerVisible,
    setLayerOpacity,
    reorderLayer,
  };
}
