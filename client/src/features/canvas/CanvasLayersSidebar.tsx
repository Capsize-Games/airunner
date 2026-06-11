import { useState, useCallback, useRef, useEffect } from "react";
import { useCanvasContext } from "./CanvasContext";
import type { CanvasLayer, LayerGroup } from "./useCanvasState";
import NewLayerModal from "./NewLayerModal";
import NewLayerMaskModal from "./NewLayerMaskModal";
import OpacitySlider from "./OpacitySlider";
import LayerRow from "./layers/LayerRow";
import GroupRow from "./layers/GroupRow";
import LayerContextMenu from "./layers/LayerContextMenu";
import LayerFooter from "./layers/LayerFooter";
import type { DragState, EditState } from "./layers/LayerRow";

export default function CanvasLayersSidebar() {
  const canvas = useCanvasContext();

  // ── Edit state ──────────────────────────────────────────────────────
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");

  const startEdit = useCallback((layer: CanvasLayer) => {
    setEditingId(layer.id);
    setEditName(layer.name);
  }, []);
  const commitEdit = useCallback((id: string) => {
    if (editName.trim()) canvas.renameLayer(id, editName.trim());
    setEditingId(null);
  }, [editName, canvas]);
  const handleEditKeyDown = useCallback((e: React.KeyboardEvent, id: string) => {
    if (e.key === "Enter") commitEdit(id);
    else if (e.key === "Escape") setEditingId(null);
  }, [commitEdit]);

  // ── Drag state ──────────────────────────────────────────────────────
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [dragPosition, setDragPosition] = useState<"above" | "below">("below");
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const dragSourceId = useRef<string | null>(null);

  const onDragStart = useCallback((id: string, e: React.DragEvent) => {
    dragSourceId.current = id;
    setDraggingId(id);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", id);
  }, []);
  const onDragOver = useCallback((id: string, e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverId(id);
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setDragPosition(e.clientY < rect.top + rect.height / 2 ? "above" : "below");
  }, []);
  const onDragLeave = useCallback(() => setDragOverId(null), []);
  const onDragEnd = useCallback(() => {
    setDragOverId(null);
    setDraggingId(null);
    dragSourceId.current = null;
  }, []);

  const performDrop = useCallback((targetId: string) => {
    const srcId = dragSourceId.current;
    if (!srcId || srcId === targetId) return;
    setDragOverId(null);
    const targetLayer = canvas.layers.find((l) => l.id === targetId);
    let toIndex = canvas.displayOrder.indexOf(targetId);
    if (dragPosition === "above") toIndex += 1;
    if (targetLayer?.parentGroupId) {
      canvas.moveLayerToGroup(srcId, targetLayer.parentGroupId, toIndex);
    } else {
      canvas.reorderDisplayItem(srcId, toIndex);
    }
  }, [canvas, dragPosition]);

  // ── Context menu ────────────────────────────────────────────────────
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; layerId: string } | null>(null);

  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [contextMenu]);

  // ── Modal state ─────────────────────────────────────────────────────
  const [showNewLayer, setShowNewLayer] = useState(false);
  const [showMaskModal, setShowMaskModal] = useState(false);

  // ── Opacity ─────────────────────────────────────────────────────────
  const activeOpacity = canvas.activeLayerId
    ? canvas.layers.find((l) => l.id === canvas.activeLayerId)?.opacity ?? 1
    : 1;

  const handleOpacityChange = useCallback((val: number) => {
    for (const id of canvas.selectedLayerIds) {
      if (canvas.layers.find((l) => l.id === id)) canvas.setLayerOpacity(id, val);
      else if (canvas.layerGroups.find((g) => g.id === id)) canvas.setGroupOpacity(id, val);
    }
    if (canvas.selectedLayerIds.length === 0 && canvas.activeLayerId) {
      canvas.setLayerOpacity(canvas.activeLayerId, val);
    }
  }, [canvas]);

  // ── Copy / delete selected ──────────────────────────────────────────
  const copySelected = useCallback(() => {
    for (const id of canvas.selectedLayerIds) {
      if (canvas.layers.find((l) => l.id === id)) canvas.addLayer();
    }
  }, [canvas]);

  const deleteSelected = useCallback(() => {
    const sorted = [...canvas.selectedLayerIds].sort(
      (a, b) =>
        canvas.layers.findIndex((l) => l.id === b) -
        canvas.layers.findIndex((l) => l.id === a),
    );
    for (const id of sorted) {
      if (canvas.layers.find((l) => l.id === id)) canvas.deleteLayer(id);
      else canvas.deleteGroup(id);
    }
  }, [canvas]);

  // ── Build render list ───────────────────────────────────────────────
  type RenderGroupItem = { type: "group"; group: LayerGroup };
  type RenderLayerItem = { type: "layer"; layer: CanvasLayer; depth: number };
  const renderItems: (RenderGroupItem | RenderLayerItem)[] = [];
  for (const id of [...canvas.displayOrder].reverse()) {
    const group = canvas.layerGroups.find((g) => g.id === id);
    if (group) {
      renderItems.push({ type: "group", group });
      if (group.expanded) {
        for (const child of [...canvas.layers].reverse().filter((l) => l.parentGroupId === group.id)) {
          renderItems.push({ type: "layer", layer: child, depth: 1 });
        }
      }
      continue;
    }
    const layer = canvas.layers.find((l) => l.id === id);
    if (layer) renderItems.push({ type: "layer", layer, depth: 0 });
  }

  const displayLayerName = useCallback((layer: CanvasLayer): string => {
    const sameName = canvas.layers.filter((l) => l.name === layer.name);
    if (sameName.length <= 1) return layer.name;
    return `${layer.name} #${sameName.findIndex((l) => l.id === layer.id) + 1}`;
  }, [canvas.layers]);

  const editState: EditState = {
    editingId, editName,
    onNameChange: setEditName,
    onCommit: commitEdit,
    onKeyDown: handleEditKeyDown,
    onStart: startEdit,
  };

  return (
    <div className="flex-grow-1 d-flex flex-column overflow-hidden min-w-0">
      <OpacitySlider value={activeOpacity} onChange={handleOpacityChange} />

      <div className="scroll-panel">
        {renderItems.map((item, idx) => {
          if (item.type === "layer") {
            const dragState: DragState = {
              draggingId, dragOverId, dragPosition,
              onDragStart, onDragOver, onDragLeave, onDragEnd,
              onDrop: () => performDrop(item.layer.id),
            };
            return (
              <LayerRow
                key={item.layer.id ?? `layer-${idx}`}
                layer={item.layer}
                depth={item.depth}
                isActive={item.layer.id === canvas.activeLayerId}
                isSelected={canvas.selectedLayerIds.includes(item.layer.id)}
                displayName={displayLayerName(item.layer)}
                drag={dragState}
                edit={editState}
                onContextMenu={(x, y, id) => setContextMenu({ x, y, layerId: id })}
              />
            );
          }
          return (
            <GroupRow
              key={item.group.id ?? `group-${idx}`}
              group={item.group}
              isSelected={canvas.selectedLayerIds.includes(item.group.id)}
              onContextMenu={(x, y, id) => setContextMenu({ x, y, layerId: id })}
              drag={{
                dragOverId, dragPosition, dragSourceId,
                onDragStart, onDragOver, onDragLeave, onDragEnd,
                onClearDrag: () => setDragOverId(null),
              }}
            />
          );
        })}
      </div>

      <LayerFooter
        onAddLayer={() => setShowNewLayer(true)}
        onAddMask={() => setShowMaskModal(true)}
        onCopySelected={copySelected}
        onDeleteSelected={deleteSelected}
      />

      <LayerContextMenu contextMenu={contextMenu} onClose={() => setContextMenu(null)} />

      <NewLayerModal
        show={showNewLayer}
        layerIndex={canvas.layers.length + 1}
        defaultName={canvas.activeLayer?.name === "Background" ? "Layer" : (canvas.activeLayer?.name ?? "Layer")}
        onConfirm={(name, opacity, fillColor) => canvas.addLayer(name, opacity, fillColor)}
        onHide={() => setShowNewLayer(false)}
      />
      <NewLayerMaskModal
        show={showMaskModal}
        layerName={canvas.activeLayer?.name ?? "Layer"}
        onAdd={(fill) => {
          if (canvas.activeLayerId) canvas.addLayerMask(canvas.activeLayerId, fill);
          setShowMaskModal(false);
        }}
        onHide={() => setShowMaskModal(false)}
      />
    </div>
  );
}
