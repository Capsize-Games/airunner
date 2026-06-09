// ── Stage-Level Move Tool ────────────────────────────────────────────
// Handles both "pick" and "move-selected" modes for the Move tool at
// the Stage level so that Mode 2 (move-selected) can initiate a drag
// from empty canvas space.
//
// Mode "pick":
//   Uses stage.getIntersection() to find the shape under the cursor,
//   resolves its parent drag-group, and moves that layer/guide.
//
// Mode "move-selected":
//   Ignores getIntersection() entirely.  Moves every layer whose id
//   is in selectedLayerIds, regardless of where the user clicks.
//
// IMPORTANT – Clip counter-adjustment:
//   Each layer has an inner clipped Group whose clipX / clipY normally
//   sits at -offsetX / -offsetY so the clip window stays at (0,0) in
//   Layer space.  When we imperatively change the outer drag-group's
//   x() / y(), the clip window would shift with the Group, showing the
//   wrong slice of content.  We counteract this by also imperatively
//   shifting the clipped group's clipX / clipY by the same delta.
//   This mirrors the original per-layer manual drag in CanvasLayer.tsx.

import { useRef, useCallback, useEffect } from "react";
import Konva from "konva";
import type { MoveMode } from "../canvasTypes";
import type { CanvasLayer } from "../canvasTypes";

// ── Helpers ──────────────────────────────────────────────────────────────

/** Walk up the Konva node tree to find the drag-group for a layer. */
function findLayerDragGroup(
  shape: Konva.Shape,
): Konva.Group | null {
  let node: Konva.Node | null = shape;
  while (node) {
    const name = node.name();
    if (name && name.startsWith("layer-drag-")) {
      return node as Konva.Group;
    }
    node = node.getParent();
  }
  return null;
}

/** Extract the layerId from a drag-group name (e.g. "layer-drag-layer_3"). */
function layerIdFromDragGroup(group: Konva.Group): string | null {
  const name = group.name();
  if (!name) return null;
  const prefix = "layer-drag-";
  return name.startsWith(prefix) ? name.slice(prefix.length) : null;
}

/** Snap a value to the grid if snapping is enabled. */
function snapVal(v: number, on: boolean, gridSize: number): number {
  return on ? Math.round(v / gridSize) * gridSize : v;
}

// ── Interface ────────────────────────────────────────────────────────────

export interface MoveToolParams {
  stageRef: React.RefObject<Konva.Stage>;
  moveMode: MoveMode;
  selectedLayerIds: string[];
  layers: CanvasLayer[];
  snapToGrid: boolean;
  gridSize: number;
  onMoveLayer: (layerId: string, x: number, y: number) => void;
  onSetActiveLayer?: (layerId: string) => void;
}

export interface MoveToolHandlers {
  handleMoveMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => void;
  handleMoveMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => void;
  handleMoveMouseUp: (e: Konva.KonvaEventObject<MouseEvent>) => void;
}

// ── Hook ─────────────────────────────────────────────────────────────────

export function moveTool({
  stageRef,
  moveMode,
  selectedLayerIds,
  layers,
  snapToGrid,
  gridSize,
  onMoveLayer,
  onSetActiveLayer,
}: MoveToolParams): MoveToolHandlers {
  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const targetLayerIds = useRef<string[]>([]);
  const initialPositions = useRef<Map<string, { x: number; y: number }>>(
    new Map(),
  );

  // ── Resolve drag group nodes for given layer IDs ───────────────────
  const findDragGroups = useCallback(
    (ids: string[]): Map<string, Konva.Group> => {
      const stage = stageRef.current;
      if (!stage) return new Map();
      const map = new Map<string, Konva.Group>();
      for (const id of ids) {
        const group = stage.findOne<Konva.Group>(
          `.layer-drag-${id}`,
        );
        if (group) map.set(id, group);
      }
      return map;
    },
    [stageRef],
  );

  // ── Find and adjust the inner clipped group for a given layer ID ───
  // Returns the clipped Konva.Group, or undefined if not found.
  const findclipGroup = useCallback(
    (layerId: string): Konva.Group | undefined => {
      const stage = stageRef.current;
      if (!stage) return;
      return stage.findOne<Konva.Group>(
        `.layer-clip-${layerId}`,
      );
    },
    [stageRef],
  );

  // ── Imperatively update one layer's drag-group position AND its ────
  //    inner clipped group's clipX / clipY.
  const applyPosition = useCallback(
    (id: string, group: Konva.Group, x: number, y: number) => {
      group.x(x);
      group.y(y);

      // Counteract the drag-group's position change by shifting the
      // inner clipped group's clip offsets in the opposite direction.
      // Without this the clip window would shift with the group,
      // showing the wrong slice of content (or nothing at all).
      const clipped = findclipGroup(id);
      if (clipped) {
        clipped.clipX(-x);
        clipped.clipY(-y);
      }
    },
    [findclipGroup],
  );

  // ── Mouse down ─────────────────────────────────────────────────────
  const handleMoveMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>) => {
      if (e.evt.button !== 0) return; // left button only
      const stage = stageRef.current;
      if (!stage) return;
      const pos = stage.getPointerPosition();
      if (!pos) return;

      let ids: string[] = [];

      if (moveMode === "pick") {
        // Find the topmost visible shape at pointer position.
        const shape = stage.getIntersection(pos);
        if (!shape) return; // clicked on empty area – nothing to move

        // Walk up to find the drag-group for this shape's layer.
        const dragGroup = findLayerDragGroup(shape);
        if (!dragGroup) return;
        const layerId = layerIdFromDragGroup(dragGroup);
        if (!layerId) return;

        // Make this the active layer so the UI reflects the pick.
        onSetActiveLayer?.(layerId);
        ids = [layerId];
      } else {
        // "move-selected": move all currently selected layers.
        ids = selectedLayerIds.filter((id) =>
          layers.some((l) => l.id === id),
        );
        if (ids.length === 0) return;
      }

      // Record starting state for every target.
      const groups = findDragGroups(ids);
      if (groups.size === 0) return;

      const initPos = new Map<string, { x: number; y: number }>();
      for (const [id, group] of groups) {
        initPos.set(id, { x: group.x(), y: group.y() });
      }

      isDragging.current = true;
      dragStart.current = { x: pos.x, y: pos.y };
      targetLayerIds.current = ids;
      initialPositions.current = initPos;
    },
    [
      stageRef,
      moveMode,
      selectedLayerIds,
      layers,
      findDragGroups,
      onSetActiveLayer,
    ],
  );

  // ── Mouse move ─────────────────────────────────────────────────────
  const handleMoveMouseMove = useCallback(
    (_e: Konva.KonvaEventObject<MouseEvent>) => {
      if (!isDragging.current) return;
      const stage = stageRef.current;
      if (!stage) return;
      const pos = stage.getPointerPosition();
      if (!pos) return;

      const dx = pos.x - dragStart.current.x;
      const dy = pos.y - dragStart.current.y;

      const groups = findDragGroups(targetLayerIds.current);
      for (const [id, group] of groups) {
        const init = initialPositions.current.get(id);
        if (!init) continue;
        applyPosition(id, group, init.x + dx, init.y + dy);
      }

      // Batch-draw all affected layers.
      const drawn = new Set<Konva.Layer>();
      for (const [, group] of groups) {
        const layer = group.getLayer();
        if (layer && !drawn.has(layer)) {
          drawn.add(layer);
          layer.batchDraw();
        }
      }
    },
    [stageRef, findDragGroups, applyPosition],
  );

  // ── Mouse up ───────────────────────────────────────────────────────
  const handleMoveMouseUp = useCallback(
    (_e: Konva.KonvaEventObject<MouseEvent>) => {
      if (!isDragging.current) return;
      isDragging.current = false;

      const groups = findDragGroups(targetLayerIds.current);
      for (const [id, group] of groups) {
        const x = snapVal(group.x(), snapToGrid, gridSize);
        const y = snapVal(group.y(), snapToGrid, gridSize);
        applyPosition(id, group, x, y);
        group.getLayer()?.batchDraw();
        // Only commit if position actually changed from stored state.
        const init = initialPositions.current.get(id);
        if (init && (init.x !== x || init.y !== y)) {
          onMoveLayer(id, x, y);
        }
      }

      targetLayerIds.current = [];
      initialPositions.current = new Map();
    },
    [stageRef, snapToGrid, gridSize, onMoveLayer, findDragGroups, applyPosition],
  );

  // ── Global pointerup to catch releases outside the Stage ───────────
  useEffect(() => {
    const onGlobalUp = () => {
      if (!isDragging.current) return;
      isDragging.current = false;
      const groups = findDragGroups(targetLayerIds.current);
      for (const [id, group] of groups) {
        const x = snapVal(group.x(), snapToGrid, gridSize);
        const y = snapVal(group.y(), snapToGrid, gridSize);
        applyPosition(id, group, x, y);
        group.getLayer()?.batchDraw();
        const init = initialPositions.current.get(id);
        if (init && (init.x !== x || init.y !== y)) {
          onMoveLayer(id, x, y);
        }
      }
      targetLayerIds.current = [];
      initialPositions.current = new Map();
    };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup", onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup", onGlobalUp);
    };
  }, [snapToGrid, gridSize, onMoveLayer, findDragGroups, applyPosition]);

  return {
    handleMoveMouseDown,
    handleMoveMouseMove,
    handleMoveMouseUp,
  };
}
