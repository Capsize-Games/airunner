// ── Canvas Group Operations ─────────────────────────────────────────────
import { useCallback } from "react";
import { nextGroupId } from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

export function groups(
  { setState, recordSnapshot }: CanvasSetters,
) {
  const addLayerGroup = useCallback(() => {
    const id = nextGroupId();
    setState((prev) =>
      recordSnapshot({
        ...prev,
        layerGroups: [
          ...prev.layerGroups,
          {
            id,
            name: `Group ${prev.layerGroups.length + 1}`,
            expanded: true,
            visible: true,
            opacity: 1,
          },
        ],
        displayOrder: [...prev.displayOrder, id],
      }),
    );
  }, [setState, recordSnapshot]);

  const toggleGroupExpanded = useCallback(
    (id: string) => {
      setState((prev) => ({
        ...prev,
        layerGroups: prev.layerGroups.map((g) =>
          g.id === id ? { ...g, expanded: !g.expanded } : g,
        ),
      }));
    },
    [setState],
  );

  const renameGroup = useCallback(
    (id: string, name: string) => {
      setState((prev) => ({
        ...prev,
        layerGroups: prev.layerGroups.map((g) =>
          g.id === id ? { ...g, name } : g,
        ),
      }));
    },
    [setState],
  );

  const setGroupVisible = useCallback(
    (id: string, visible: boolean) => {
      setState((prev) => ({
        ...prev,
        _ts: Date.now(),
        layerGroups: prev.layerGroups.map((g) =>
          g.id === id ? { ...g, visible } : g,
        ),
      }));
    },
    [setState],
  );

  const setGroupOpacity = useCallback(
    (id: string, opacity: number) => {
      setState((prev) => ({
        ...prev,
        _ts: Date.now(),
        layerGroups: prev.layerGroups.map((g) =>
          g.id === id ? { ...g, opacity } : g,
        ),
      }));
    },
    [setState],
  );

  const deleteGroup = useCallback(
    (id: string) => {
      setState((prev) => {
        const groupLayerIds = new Set(
          prev.layers
            .filter((l) => l.parentGroupId === id)
            .map((l) => l.id),
        );
        const remainingLayers = prev.layers.filter(
          (l) => !groupLayerIds.has(l.id),
        );
        let newActive = prev.activeLayerId;
        if (newActive && groupLayerIds.has(newActive)) {
          newActive = remainingLayers.at(-1)?.id ?? null;
        }
        return recordSnapshot({
          ...prev,
          layerGroups: prev.layerGroups.filter(
            (g) => g.id !== id,
          ),
          layers: remainingLayers,
          displayOrder: prev.displayOrder.filter(
            (oid) => oid !== id && !groupLayerIds.has(oid),
          ),
          activeLayerId: newActive,
          selectedLayerIds:
            newActive &&
            prev.selectedLayerIds.some((s) =>
              groupLayerIds.has(s),
            )
              ? [newActive]
              : prev.selectedLayerIds.filter(
                  (s) => !groupLayerIds.has(s),
                ),
        });
      });
    },
    [setState, recordSnapshot],
  );

  const moveLayerToGroup = useCallback(
    (
      layerId: string,
      groupId: string | null,
      toIndex?: number,
    ) => {
      setState((prev) => {
        const layers = prev.layers.map((l) =>
          l.id === layerId
            ? { ...l, parentGroupId: groupId }
            : l,
        );

        let displayOrder = prev.displayOrder;
        if (groupId !== null) {
          displayOrder = displayOrder.filter(
            (id) => id !== layerId,
          );
        } else {
          if (!displayOrder.includes(layerId)) {
            displayOrder = [...displayOrder, layerId];
          }
        }

        if (toIndex === undefined) {
          return recordSnapshot({
            ...prev,
            layers,
            displayOrder,
          });
        }

        const fromIdx = layers.findIndex(
          (l) => l.id === layerId,
        );
        if (fromIdx === -1) {
          return recordSnapshot({
            ...prev,
            layers,
            displayOrder,
          });
        }
        const moved = layers.splice(fromIdx, 1);
        const adjusted =
          toIndex > fromIdx ? toIndex - 1 : toIndex;
        layers.splice(adjusted, 0, moved[0]);
        return recordSnapshot({
          ...prev,
          layers,
          displayOrder,
        });
      });
    },
    [setState, recordSnapshot],
  );

  const reorderDisplayItem = useCallback(
    (id: string, toIndex: number) => {
      setState((prev) => {
        const fromIdx = prev.displayOrder.indexOf(id);
        if (fromIdx === -1 || fromIdx === toIndex) return prev;
        const order = [...prev.displayOrder];
        const [moved] = order.splice(fromIdx, 1);
        const adjusted =
          toIndex > fromIdx ? toIndex - 1 : toIndex;
        order.splice(adjusted, 0, moved);
        return recordSnapshot({
          ...prev,
          displayOrder: order,
        });
      });
    },
    [setState, recordSnapshot],
  );

  return {
    addLayerGroup,
    toggleGroupExpanded,
    renameGroup,
    setGroupVisible,
    setGroupOpacity,
    deleteGroup,
    moveLayerToGroup,
    reorderDisplayItem,
  };
}
