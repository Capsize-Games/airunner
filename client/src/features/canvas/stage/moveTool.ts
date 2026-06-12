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
import type { MoveMode, CanvasLayer, LayerGroup } from "../canvasTypes";

// ── Helpers ──────────────────────────────────────────────────────────────

/**
 * Sample the alpha of a loaded HTMLImageElement at pixel (localX, localY)
 * within its display bounds (displayW × displayH). Returns 0–255.
 */
function sampleImageAlpha(
  imgEl: HTMLImageElement,
  localX: number,
  localY: number,
  displayW: number,
  displayH: number,
): number {
  try {
    const srcX = (localX / displayW) * imgEl.naturalWidth;
    const srcY = (localY / displayH) * imgEl.naturalHeight;
    const tmp = document.createElement("canvas");
    tmp.width = 1;
    tmp.height = 1;
    const ctx = tmp.getContext("2d");
    if (!ctx) return 0;
    ctx.drawImage(imgEl, srcX, srcY, 1, 1, 0, 0, 1, 1);
    return ctx.getImageData(0, 0, 1, 1).data[3];
  } catch {
    return 0;
  }
}

/**
 * Returns ordered visible layer IDs bottom-to-top, matching the compositing
 * order of StageContent (same logic as orderVisibleLayers in compositeCanvas).
 */
function orderedVisibleIds(
  displayOrder: string[],
  layers: CanvasLayer[],
  layerGroups: LayerGroup[],
): string[] {
  const groupVisible = (id: string | null | undefined): boolean => {
    if (!id) return true;
    const g = layerGroups.find((grp) => grp.id === id);
    return g ? g.visible : true;
  };
  const result: string[] = [];
  const seen = new Set<string>();
  const push = (layer: CanvasLayer) => {
    if (seen.has(layer.id)) return;
    seen.add(layer.id);
    if (layer.visible && groupVisible(layer.parentGroupId)) result.push(layer.id);
  };
  for (const id of displayOrder) {
    const grp = layerGroups.find((g) => g.id === id);
    if (grp) {
      layers.filter((l) => l.parentGroupId === id).forEach(push);
      continue;
    }
    const layer = layers.find((l) => l.id === id);
    if (layer) push(layer);
  }
  layers.forEach(push);
  return result;
}

/**
 * Transparency-aware layer pick. Iterates visible layers from top to bottom
 * and returns the first layer ID that has a non-transparent pixel at `stagePos`.
 *
 * For image nodes: samples the actual loaded HTMLImageElement alpha channel.
 * For strokes / fills / text: delegates to Konva's built-in hit detection and
 * checks whether the hit shape belongs to that layer's drag group.
 */
function pickLayerAtPos(
  stage: Konva.Stage,
  layers: CanvasLayer[],
  layerGroups: LayerGroup[],
  displayOrder: string[],
  stagePos: { x: number; y: number },
): string | null {
  const scale = stage.scaleX();
  const worldX = (stagePos.x - stage.x()) / scale;
  const worldY = (stagePos.y - stage.y()) / scale;

  // Pre-compute Konva hit shape for stroke/fill/text layers (cheap, not for images).
  const hitShape = stage.getIntersection(stagePos);

  // Top-to-bottom = reverse of the bottom-to-top display order.
  const bottomToTop = orderedVisibleIds(displayOrder, layers, layerGroups);
  for (let i = bottomToTop.length - 1; i >= 0; i--) {
    const layerId = bottomToTop[i];
    const layer = layers.find((l) => l.id === layerId);
    if (!layer) continue;

    const dragGroup = stage.findOne<Konva.Group>(`.layer-drag-${layerId}`);
    if (!dragGroup) continue;

    const gx = dragGroup.x();
    const gy = dragGroup.y();

    // ── Image pixel sampling ─────────────────────────────────────────
    if (layer.images.length > 0) {
      const imgNodes = dragGroup.find<Konva.Image>("Image");
      for (const imgNode of imgNodes) {
        const nx = gx + imgNode.x();
        const ny = gy + imgNode.y();
        const nw = imgNode.width();
        const nh = imgNode.height();
        if (worldX < nx || worldX >= nx + nw || worldY < ny || worldY >= ny + nh) continue;
        const imgEl = imgNode.image() as HTMLImageElement | null;
        if (!imgEl || !imgEl.complete) return layerId; // treat unloaded as opaque
        const alpha = sampleImageAlpha(imgEl, worldX - nx, worldY - ny, nw, nh);
        if (alpha > 10) return layerId;
      }
    }

    // ── Stroke / fill / text: use Konva's hit detection ─────────────
    if ((layer.strokes.length > 0 || layer.fillColor || layer.textNode) && hitShape) {
      let node: Konva.Node | null = hitShape;
      while (node) {
        if (node === dragGroup) return layerId;
        node = node.getParent();
      }
    }
  }

  return null;
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
  layerGroups: LayerGroup[];
  displayOrder: string[];
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
  layerGroups,
  displayOrder,
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
        // Transparency-aware pick: iterate layers top-to-bottom and sample
        // actual pixel alpha so transparent areas of upper layers are ignored.
        const layerId = pickLayerAtPos(stage, layers, layerGroups, displayOrder, pos);
        if (!layerId) return; // clicked on fully transparent / empty area

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
      layerGroups,
      displayOrder,
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

      const scale = stage.scaleX();
      const dx = (pos.x - dragStart.current.x) / scale;
      const dy = (pos.y - dragStart.current.y) / scale;

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
