// ── Canvas State Hook ────────────────────────────────────────────────────────
// Re-export types for backward compatibility.
export type {
  CanvasState,
  CanvasLayer,
  ActiveGridArea,
  ActiveTool,
  ImageNode,
  StrokeNode,
  LayerGroup,
  FilterConfig,
} from "./canvasTypes";

import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import type {
  CanvasState as CS, CanvasLayer as CL, ActiveGridArea as AGA,
  ActiveTool as AT, ImageNode as IN, StrokeNode as SN,
  LayerGroup as LG, FilterConfig as FC,
} from "./canvasTypes";
import {
  nextLayerId, nextStrokeId, nextImageId, nextGroupId,
  advanceCountersFromState, snapTo8, pushHistory, serialize,
  defaultState, loadPersistedState, persistState,
} from "./canvasStateUtils";

// ── Hook ────────────────────────────────────────────────────────────────────

export function useCanvasState() {
  const [state, setState] = useState<CS>(
    () => loadPersistedState() ?? defaultState(),
  );
  const persistTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced localStorage persistence.
  useEffect(() => {
    if (persistTimer.current) clearTimeout(persistTimer.current);
    persistTimer.current = setTimeout(() => persistState(state), 300);
    return () => {
      if (persistTimer.current) clearTimeout(persistTimer.current);
    };
  }, [state]);

  const recordSnapshot = useCallback(
    (prev: CS): CS => {
      const snapshot = serialize(prev);
      const { history, historyIndex } = pushHistory(
        prev.history, prev.historyIndex, snapshot,
      );
      return {
        ...prev, _ts: Date.now(), history, historyIndex,
      };
    },
    [],
  );

  // ── Layer operations ──────────────────────────────────────────────────────

  const addLayer = useCallback(
    (name?: string, opacity?: number) => {
      setState((prev) => {
        const newLayer: CL = {
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
    [recordSnapshot],
  );

  const deleteLayer = useCallback((id: string) => {
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
        displayOrder: prev.displayOrder.filter((oid) => oid !== id),
        activeLayerId: newActive,
        selectedLayerIds:
          cleanedSelection.length > 0
            ? cleanedSelection
            : newActive
              ? [newActive]
              : [],
      });
    });
  }, [recordSnapshot]);

  const renameLayer = useCallback((id: string, name: string) => {
    setState((prev) => ({
      ...prev,
      layers: prev.layers.map(
        (l) => (l.id === id ? { ...l, name } : l),
      ),
    }));
  }, []);

  const setLayerVisible = useCallback(
    (id: string, visible: boolean) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map(
          (l) => (l.id === id ? { ...l, visible } : l),
        ),
      }));
    },
    [],
  );

  const setLayerOpacity = useCallback(
    (id: string, opacity: number) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map(
          (l) => (l.id === id ? { ...l, opacity } : l),
        ),
      }));
    },
    [],
  );

  const reorderLayer = useCallback(
    (id: string, direction: "up" | "down") => {
      setState((prev) => {
        const idx = prev.layers.findIndex((l) => l.id === id);
        if (idx === -1) return prev;
        const layers = [...prev.layers];
        if (direction === "up" && idx < layers.length - 1) {
          [layers[idx], layers[idx + 1]] = [
            layers[idx + 1], layers[idx],
          ];
        } else if (direction === "down" && idx > 0) {
          [layers[idx], layers[idx - 1]] = [
            layers[idx - 1], layers[idx],
          ];
        } else return prev;
        return recordSnapshot({ ...prev, layers });
      });
    },
    [recordSnapshot],
  );

  const setActiveLayer = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      activeLayerId: id,
      selectedLayerIds: [id],
    }));
  }, []);

  // ── Layer group operations ────────────────────────────────────────────────

  const addLayerGroup = useCallback(() => {
    const id = nextGroupId();
    setState((prev) => ({
      ...prev,
      _ts: Date.now(),
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
    }));
  }, []);

  const toggleGroupExpanded = useCallback((id: string) => {
    setState((prev) => ({
      ...prev,
      layerGroups: prev.layerGroups.map(
        (g) => g.id === id ? { ...g, expanded: !g.expanded } : g,
      ),
    }));
  }, []);

  const renameGroup = useCallback((id: string, name: string) => {
    setState((prev) => ({
      ...prev,
      layerGroups: prev.layerGroups.map(
        (g) => g.id === id ? { ...g, name } : g,
      ),
    }));
  }, []);

  const setGroupVisible = useCallback(
    (id: string, visible: boolean) => {
      setState((prev) => ({
        ...prev,
        _ts: Date.now(),
        layerGroups: prev.layerGroups.map(
          (g) => g.id === id ? { ...g, visible } : g,
        ),
      }));
    },
    [],
  );

  const setGroupOpacity = useCallback(
    (id: string, opacity: number) => {
      setState((prev) => ({
        ...prev,
        _ts: Date.now(),
        layerGroups: prev.layerGroups.map(
          (g) => g.id === id ? { ...g, opacity } : g,
        ),
      }));
    },
    [],
  );

  const deleteGroup = useCallback((id: string) => {
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
      return {
        ...prev,
        _ts: Date.now(),
        layerGroups: prev.layerGroups.filter((g) => g.id !== id),
        layers: remainingLayers,
        displayOrder: prev.displayOrder.filter(
          (oid) => oid !== id && !groupLayerIds.has(oid),
        ),
        activeLayerId: newActive,
        selectedLayerIds:
          newActive &&
            prev.selectedLayerIds.some((s) => groupLayerIds.has(s))
            ? [newActive]
            : prev.selectedLayerIds.filter(
              (s) => !groupLayerIds.has(s),
            ),
      };
    });
  }, []);

  const moveLayerToGroup = useCallback(
    (layerId: string, groupId: string | null, toIndex?: number) => {
      setState((prev) => {
        const layers = prev.layers.map(
          (l) => l.id === layerId
            ? { ...l, parentGroupId: groupId }
            : l,
        );

        let displayOrder = prev.displayOrder;
        if (groupId !== null) {
          displayOrder = displayOrder.filter((id) => id !== layerId);
        } else {
          if (!displayOrder.includes(layerId)) {
            displayOrder = [...displayOrder, layerId];
          }
        }

        if (toIndex === undefined) {
          return {
            ...prev, _ts: Date.now(), layers, displayOrder,
          };
        }

        const fromIdx = layers.findIndex((l) => l.id === layerId);
        if (fromIdx === -1) {
          return { ...prev, _ts: Date.now(), layers, displayOrder };
        }
        const moved = layers.splice(fromIdx, 1);
        const adjusted = toIndex > fromIdx ? toIndex - 1 : toIndex;
        layers.splice(adjusted, 0, moved[0]);
        return { ...prev, _ts: Date.now(), layers, displayOrder };
      });
    },
    [],
  );

  const reorderDisplayItem = useCallback(
    (id: string, toIndex: number) => {
      setState((prev) => {
        const fromIdx = prev.displayOrder.indexOf(id);
        if (fromIdx === -1 || fromIdx === toIndex) return prev;
        const order = [...prev.displayOrder];
        const [moved] = order.splice(fromIdx, 1);
        const adjusted = toIndex > fromIdx ? toIndex - 1 : toIndex;
        order.splice(adjusted, 0, moved);
        return { ...prev, _ts: Date.now(), displayOrder: order };
      });
    },
    [],
  );

  const toggleLayerSelection = useCallback((id: string) => {
    setState((prev) => {
      const isSelected = prev.selectedLayerIds.includes(id);
      const nextSelection = isSelected
        ? prev.selectedLayerIds.filter((s) => s !== id)
        : [...prev.selectedLayerIds, id];
      if (nextSelection.length === 0) return prev;
      return {
        ...prev,
        selectedLayerIds: nextSelection,
      };
    });
  }, []);

  const selectLayerRange = useCallback((id: string) => {
    setState((prev) => {
      const startIdx = prev.layers.findIndex(
        (l) => l.id === prev.activeLayerId,
      );
      const endIdx = prev.layers.findIndex((l) => l.id === id);
      if (startIdx === -1 || endIdx === -1) return prev;
      const lo = Math.min(startIdx, endIdx);
      const hi = Math.max(startIdx, endIdx);
      const rangeIds = prev.layers.slice(lo, hi + 1).map((l) => l.id);
      return {
        ...prev,
        selectedLayerIds: rangeIds,
        activeLayerId: id,
      };
    });
  }, []);

  const reorderLayerToIndex = useCallback(
    (id: string, toIndex: number) => {
      setState((prev) => {
        const fromIdx = prev.layers.findIndex((l) => l.id === id);
        if (fromIdx === -1 || fromIdx === toIndex) return prev;
        const layers = [...prev.layers];
        const [moved] = layers.splice(fromIdx, 1);
        const adjusted = toIndex > fromIdx ? toIndex - 1 : toIndex;
        layers.splice(adjusted, 0, moved);
        return recordSnapshot({ ...prev, layers });
      });
    },
    [recordSnapshot],
  );

  const mergeSelectedLayers = useCallback(() => {
    setState((prev) => {
      const sel = prev.selectedLayerIds;
      if (sel.length < 1) return prev;

      const sorted = [...sel]
        .map(
          (id) => ({
            id,
            idx: prev.layers.findIndex((l) => l.id === id),
          }),
        )
        .filter((e) => e.idx !== -1)
        .sort((a, b) => a.idx - b.idx);

      if (sorted.length === 0) return prev;

      const targetIdx = sorted[0].idx - 1;
      if (targetIdx < 0) return prev;

      const targetId = prev.layers[targetIdx].id;
      const mergeIds = new Set(sorted.map((e) => e.id));

      const extraImages: IN[] = [];
      const extraStrokes: SN[] = [];
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
  }, [recordSnapshot]);

  // ── Active tool ───────────────────────────────────────────────────────────

  const setActiveTool = useCallback((tool: AT) => {
    setState((prev) => ({ ...prev, activeTool: tool }));
  }, []);

  // ── Active grid area ──────────────────────────────────────────────────────

  const setActiveGridArea = useCallback((area: AGA) => {
    setState((prev) => ({
      ...prev,
      activeGridArea: {
        x: Math.max(0, snapTo8(area.x)),
        y: Math.max(0, snapTo8(area.y)),
        width: Math.max(8, snapTo8(area.width)),
        height: Math.max(8, snapTo8(area.height)),
      },
    }));
  }, []);

  // ── Reset document ────────────────────────────────────────────────────────

  const resetDocument = useCallback(() => {
    try {
      localStorage.removeItem("airunner_canvas_state");
    } catch { /* noop */ }
    setState((prev) => ({
      ...defaultState(),
      _ts: Date.now(),
      brushSize: prev.brushSize,
      brushColor: prev.brushColor,
    }));
  }, []);

  // ── Move layer ────────────────────────────────────────────────────────────

  const moveLayer = useCallback(
    (id: string, x: number, y: number) => {
      setState((prev) => recordSnapshot({
        ...prev,
        layers: prev.layers.map(
          (l) => l.id === id
            ? { ...l, offsetX: x, offsetY: y }
            : l,
        ),
      }));
    },
    [recordSnapshot],
  );

  // ── Document settings ─────────────────────────────────────────────────────

  const setDocumentSize = useCallback(
    (width: number, height: number) => {
      setState(
        (prev) => recordSnapshot({
          ...prev,
          documentWidth: width,
          documentHeight: height,
        }),
      );
    },
    [recordSnapshot],
  );

  const setDocumentBgColor = useCallback((color: string) => {
    setState((prev) => ({ ...prev, documentBgColor: color }));
  }, []);

  // ── Snap to grid ──────────────────────────────────────────────────────────

  const setSnapToGrid = useCallback((on: boolean) => {
    setState((prev) => ({ ...prev, snapToGrid: on }));
  }, []);

  // ── Image placement ───────────────────────────────────────────────────────

  const placeImageOnNewLayer = useCallback(
    (base64: string, x: number, y: number,
      width: number, height: number,
    ) => {
      setState((prev) => {
        const newLayerId = nextLayerId();
        const newImage: IN = {
          id: nextImageId(),
          x, y, width, height,
          src: base64.startsWith("data:")
            ? base64
            : `data:image/png;base64,${base64}`,
        };
        const newLayer: CL = {
          id: newLayerId,
          name: `Image ${prev.layers.length + 1}`,
          visible: true,
          opacity: 1,
          filters: [],
          images: [newImage],
          strokes: [],
          offsetX: 0,
          offsetY: 0,
          parentGroupId: null,
        };
        const next = {
          ...prev,
          layers: [...prev.layers, newLayer],
          activeLayerId: newLayerId,
        };
        const { history, historyIndex } = pushHistory(
          prev.history, prev.historyIndex, serialize(next),
        );
        return { ...next, history, historyIndex };
      });
    },
    [],
  );

  const placeImage = useCallback(
    (base64: string, x: number, y: number,
      width: number, height: number,
    ) => {
      setState((prev) => {
        const activeIdx = prev.layers.findIndex(
          (l) => l.id === prev.activeLayerId,
        );
        if (activeIdx === -1) return prev;
        const newImage: IN = {
          id: nextImageId(),
          x, y, width, height,
          src: base64.startsWith("data:")
            ? base64
            : `data:image/png;base64,${base64}`,
        };
        const layers = prev.layers.map(
          (l, i) =>
            i === activeIdx
              ? { ...l, images: [...l.images, newImage] }
              : l,
        );
        return recordSnapshot({ ...prev, layers });
      });
    },
    [recordSnapshot],
  );

  const moveImage = useCallback(
    (layerId: string, imageId: string, x: number, y: number) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map((l) =>
          l.id !== layerId
            ? l
            : {
              ...l,
              images: l.images.map(
                (img) => img.id === imageId
                  ? { ...img, x, y }
                  : img,
              ),
            },
        ),
      }));
    },
    [],
  );

  // ── Strokes ───────────────────────────────────────────────────────────────

  const addStroke = useCallback(
    (stroke: Omit<SN, "id">) => {
      setState((prev) => {
        const activeIdx = prev.layers.findIndex(
          (l) => l.id === prev.activeLayerId,
        );
        if (activeIdx === -1) return prev;
        const newStroke: SN = {
          ...stroke, id: nextStrokeId(),
        };
        const layers = prev.layers.map(
          (l, i) =>
            i === activeIdx
              ? { ...l, strokes: [...l.strokes, newStroke] }
              : l,
        );
        const next = { ...prev, _ts: Date.now(), layers };
        const { history, historyIndex } = pushHistory(
          prev.history, prev.historyIndex, serialize(next),
        );
        return { ...next, history, historyIndex };
      });
    },
    [],
  );

  const addMaskStroke = useCallback(
    (stroke: Omit<SN, "id">) => {
      setState((prev) => {
        const newStroke: SN = {
          ...stroke, id: nextStrokeId(),
        };
        const next = {
          ...prev,
          _ts: Date.now(),
          maskStrokes: [...prev.maskStrokes, newStroke],
        };
        const { history, historyIndex } = pushHistory(
          prev.history, prev.historyIndex, serialize(next),
        );
        return { ...next, history, historyIndex };
      });
    },
    [],
  );

  const clearMask = useCallback(() => {
    setState((prev) => {
      const next = { ...prev, maskStrokes: [] };
      const { history, historyIndex } = pushHistory(
        prev.history, prev.historyIndex, serialize(next),
      );
      return { ...next, history, historyIndex };
    });
  }, []);

  // ── Filters ───────────────────────────────────────────────────────────────

  const setLayerFilters = useCallback(
    (id: string, filters: FC[]) => {
      setState((prev) => ({
        ...prev,
        layers: prev.layers.map(
          (l) => (l.id === id ? { ...l, filters } : l),
        ),
      }));
    },
    [],
  );

  // ── Undo / Redo ───────────────────────────────────────────────────────────

  const parseSnapshot = (json: string): Partial<CS> => {
    try { return JSON.parse(json); } catch { return {}; }
  };

  const undo = useCallback(() => {
    setState((prev) => {
      if (prev.historyIndex <= 0) return prev;
      const newIndex = prev.historyIndex - 1;
      return {
        ...prev,
        ...parseSnapshot(prev.history[newIndex]),
        historyIndex: newIndex,
      };
    });
  }, []);

  const redo = useCallback(() => {
    setState((prev) => {
      if (prev.historyIndex >= prev.history.length - 1) return prev;
      const newIndex = prev.historyIndex + 1;
      return {
        ...prev,
        ...parseSnapshot(prev.history[newIndex]),
        historyIndex: newIndex,
      };
    });
  }, []);

  // ── Serialization ─────────────────────────────────────────────────────────

  const getSerializedState = useCallback(
    (): CS => state, [state],
  );

  const getPersistableState = useCallback(() => {
    const { history, historyIndex, ...rest } = state;
    return rest;
  }, [state]);

  const loadFromJSON = useCallback((json: string) => {
    try {
      const data = JSON.parse(json);
      advanceCountersFromState(data);
      setState((prev) => {
        const incomingTs = (
          data as { _ts?: number }
        )._ts ?? 0;
        if (incomingTs > 0 && incomingTs <= prev._ts) {
          return prev;
        }
        let displayOrder = data.displayOrder;
        if (
          !Array.isArray(displayOrder) ||
          displayOrder.length === 0
        ) {
          const groupIds = (
            data.layerGroups ?? []
          ).map((g: LG) => g.id);
          const ungroupedIds = (data.layers ?? [])
            .filter((l: CL) => !l.parentGroupId)
            .map((l: CL) => l.id);
          displayOrder = [...groupIds, ...ungroupedIds];
        }
        return {
          ...prev,
          _ts: Math.max(prev._ts, incomingTs),
          displayOrder,
          layerGroups: data.layerGroups ?? prev.layerGroups,
          layers: (data.layers || prev.layers).map(
            (l: CL) => ({
              ...l,
              offsetX: l.offsetX ?? 0,
              offsetY: l.offsetY ?? 0,
              parentGroupId: l.parentGroupId ?? null,
            }),
          ),
          activeLayerId: data.activeLayerId ??
            prev.activeLayerId,
          selectedLayerIds: data.selectedLayerIds ??
            prev.selectedLayerIds,
          activeGridArea: data.activeGridArea ||
            prev.activeGridArea,
          activeTool: data.activeTool || "brush",
          brushSize: data.brushSize ?? prev.brushSize,
          brushColor: data.brushColor || prev.brushColor,
          maskStrokes: data.maskStrokes || [],
          documentWidth: data.documentWidth ??
            prev.documentWidth,
          documentHeight: data.documentHeight ??
            prev.documentHeight,
          documentBgColor: data.documentBgColor ??
            prev.documentBgColor,
          snapToGrid: data.snapToGrid ?? prev.snapToGrid,
        };
      });
    } catch { /* ignore */ }
  }, []);

  // ── Brush controls ────────────────────────────────────────────────────────

  const setBrushSize = useCallback((size: number) => {
    setState((prev) => ({ ...prev, brushSize: Math.max(1, size) }));
  }, []);

  const setBrushColor = useCallback((color: string) => {
    setState((prev) => ({ ...prev, brushColor: color }));
  }, []);

  // ── Derived ───────────────────────────────────────────────────────────────

  const activeLayer = useMemo(
    () => state.layers.find(
      (l) => l.id === state.activeLayerId,
    ) ?? null,
    [state.layers, state.activeLayerId],
  );

  return {
    ...state,
    activeLayer,
    addLayer,
    deleteLayer,
    renameLayer,
    setLayerVisible,
    setLayerOpacity,
    reorderLayer,
    reorderLayerToIndex,
    setActiveLayer,
    toggleLayerSelection,
    selectLayerRange,
    mergeSelectedLayers,
    addLayerGroup,
    toggleGroupExpanded,
    renameGroup,
    deleteGroup,
    setGroupVisible,
    setGroupOpacity,
    moveLayerToGroup,
    reorderDisplayItem,
    setActiveTool,
    setActiveGridArea,
    resetDocument,
    moveLayer,
    setDocumentSize,
    setDocumentBgColor,
    setSnapToGrid,
    placeImageOnNewLayer,
    placeImage,
    moveImage,
    addStroke,
    addMaskStroke,
    clearMask,
    setLayerFilters,
    undo,
    redo,
    getSerializedState,
    getPersistableState,
    loadFromJSON,
    setBrushSize,
    setBrushColor,
  };
}

export type CanvasActions = ReturnType<typeof useCanvasState>;
