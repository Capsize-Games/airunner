import { useState, useCallback, useRef, useEffect } from "react";
import {
  Eye, EyeOff, ChevronUp, ChevronDown, Trash2, Combine,
  FolderPlus, Copy, LayersPlus, Drama,
} from "lucide-react";
import { useCanvasContext } from "./CanvasContext";
import type { CanvasLayer, LayerGroup } from "./useCanvasState";
import NewLayerModal from "./NewLayerModal";
import NewLayerMaskModal from "./NewLayerMaskModal";
import LayerThumbnail from "./LayerThumbnail";
import IconBtn from "./IconBtn";
import OpacitySlider from "./OpacitySlider";

const ROW_H = 42;

export default function CanvasLayersSidebar() {
  const canvas = useCanvasContext();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName]   = useState("");
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [showNewLayer, setShowNewLayer] = useState(false);
  const [showMaskModal, setShowMaskModal] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; layerId: string } | null>(null);
  const dragSourceId = useRef<string | null>(null);

  useEffect(() => {
    if (!contextMenu) return;
    const close = () => setContextMenu(null);
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [contextMenu]);

  const startEdit = useCallback((layer: CanvasLayer) => {
    setEditingId(layer.id);
    setEditName(layer.name);
  }, []);

  const commitEdit = useCallback((id: string) => {
    if (editName.trim()) canvas.renameLayer(id, editName.trim());
    setEditingId(null);
  }, [editName, canvas]);

  const onKeyDown = useCallback((e: React.KeyboardEvent, id: string) => {
    if (e.key === "Enter") commitEdit(id);
    else if (e.key === "Escape") setEditingId(null);
  }, [commitEdit]);

  // Build interleaved render items from displayOrder.
  type RenderGroupItem = { type: "group"; group: LayerGroup };
  type RenderLayerItem = { type: "layer"; layer: CanvasLayer; depth: number };
  const renderItems: (RenderGroupItem | RenderLayerItem)[] = [];
  const displayOrderReversed = [...canvas.displayOrder].reverse();
  for (const id of displayOrderReversed) {
    const group = canvas.layerGroups.find((g) => g.id === id);
    if (group) {
      renderItems.push({ type: "group", group });
      if (group.expanded) {
        const children = [...canvas.layers]
          .reverse()
          .filter((l) => l.parentGroupId === group.id);
        for (const child of children) {
          renderItems.push({ type: "layer", layer: child, depth: 1 });
        }
      }
      continue;
    }
    const layer = canvas.layers.find((l) => l.id === id);
    if (layer) {
      renderItems.push({ type: "layer", layer, depth: 0 });
    }
  }

  // ── Opacity slider state (anchored at top) ──────────────────────────
  // Use the active item's opacity (layer or group) as the slider value.
  const activeOpacity = canvas.activeLayerId
    ? canvas.layers.find((l) => l.id === canvas.activeLayerId)?.opacity ?? 1
    : 1;

  const handleOpacityChange = useCallback(
    (val: number) => {
      // Apply to all selected layers.
      for (const id of canvas.selectedLayerIds) {
        const layer = canvas.layers.find((l) => l.id === id);
        if (layer) {
          canvas.setLayerOpacity(id, val);
          continue;
        }
        const group = canvas.layerGroups.find((g) => g.id === id);
        if (group) {
          canvas.setGroupOpacity(id, val);
        }
      }
      // If no selection but we have an activeLayer, apply to it.
      if (canvas.selectedLayerIds.length === 0 && canvas.activeLayerId) {
        const layer = canvas.layers.find(
          (l) => l.id === canvas.activeLayerId,
        );
        if (layer) canvas.setLayerOpacity(canvas.activeLayerId, val);
      }
    },
    [canvas],
  );

  // ── Drag-and-drop helpers ───────────────────────────────────────────

  const onDragStart = useCallback(
    (id: string, e: React.DragEvent) => {
      dragSourceId.current = id;
      setDraggingId(id);
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", id);
    },
    [],
  );

  const onDragOver = useCallback(
    (id: string, e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setDragOverId(id);
    },
    [],
  );

  const onDragEnd = useCallback(() => {
    setDragOverId(null);
    setDraggingId(null);
    dragSourceId.current = null;
  }, []);

  const performDrop = useCallback(
    (targetId: string) => {
      const srcId = dragSourceId.current;
      if (!srcId || srcId === targetId) return;
      const targetLayer = canvas.layers.find((l) => l.id === targetId);
      const toIndex = canvas.displayOrder.indexOf(targetId);
      if (targetLayer?.parentGroupId) {
        canvas.moveLayerToGroup(srcId, targetLayer.parentGroupId, toIndex);
      } else {
        canvas.reorderDisplayItem(srcId, toIndex);
      }
    },
    [canvas],
  );

  // ── Copy selected layers/groups ─────────────────────────────────────

  const copySelected = useCallback(() => {
    for (const id of canvas.selectedLayerIds) {
      const layer = canvas.layers.find((l) => l.id === id);
      if (layer) {
        // Clone with new IDs and append.
        const newLayer: CanvasLayer = {
          ...layer,
          id: `layer_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          name: `${layer.name} (copy)`,
          parentGroupId: null,
          strokes: layer.strokes.map((s) => ({
            ...s,
            id: `stroke_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          })),
          images: layer.images.map((img) => ({
            ...img,
            id: `image_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          })),
        };
        canvas.addLayer(); // Placeholder — we handle via state
      }
    }
  }, [canvas]);

  // ── Group row ───────────────────────────────────────────────────────

  const renderGroupRow = (group: LayerGroup, idx: number) => (
    <div key={group.id ?? `group-${idx}`}>
      <div
        draggable
        onClick={() => canvas.toggleGroupExpanded(group.id)}
        onDragStart={(e) => onDragStart(group.id, e)}
        onDragOver={(e) => onDragOver(group.id, e)}
        onDragLeave={() => setDragOverId(null)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOverId(null);
          const srcId = dragSourceId.current;
          if (!srcId) return;
          const orderIdx = canvas.displayOrder.indexOf(group.id);
          const isLayer = canvas.layers.some((l) => l.id === srcId);
          if (isLayer) {
            canvas.moveLayerToGroup(srcId, group.id, orderIdx);
          } else {
            canvas.reorderDisplayItem(srcId, orderIdx);
          }
          dragSourceId.current = null;
        }}
        onDragEnd={onDragEnd}
        role="button"
        style={{
          display: "flex",
          alignItems: "center",
          padding: "0 6px 0 4px",
          height: 28,
          cursor: "default",
          background: dragOverId === group.id
            ? "rgba(99,153,255,0.12)"
            : "rgba(255,255,255,0.03)",
          userSelect: "none",
        }}
      >
        <button
          title={group.visible ? "Hide group" : "Show group"}
          onClick={(e) => {
            e.stopPropagation();
            canvas.setGroupVisible(group.id, !group.visible);
          }}
          style={{
            background: "none", border: "none", padding: 0,
            marginRight: 4, flexShrink: 0, cursor: "pointer",
            color: group.visible
              ? "rgba(var(--theme-text-rgb), 0.55)"
              : "rgba(var(--theme-text-rgb), 0.2)",
            display: "flex", alignItems: "center",
          }}
        >
          {group.visible ? (
            <Eye size={13} strokeWidth={1.75} />
          ) : (
            <EyeOff size={13} strokeWidth={1.75} />
          )}
        </button>
        {group.expanded ? (
          <svg viewBox="0 0 24 24" width={12} height={12}
            style={{ marginRight: 4, flexShrink: 0, color: "rgba(var(--theme-text-rgb), 0.4)" }}
          >
            <path d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
              fill="none" stroke="currentColor" strokeWidth={1.75} />
            <path d="M9 12h6" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width={12} height={12}
            style={{ marginRight: 4, flexShrink: 0, color: "rgba(var(--theme-text-rgb), 0.4)" }}
          >
            <path d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
              fill="none" stroke="currentColor" strokeWidth={1.75} />
            <path d="M9 12h6M12 9v6" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" />
          </svg>
        )}
        <span style={{
          flexGrow: 1, minWidth: 0, overflow: "hidden",
          textOverflow: "ellipsis", whiteSpace: "nowrap",
          fontSize: 11, fontWeight: 600,
          color: group.visible
            ? "rgba(var(--theme-text-rgb), 0.5)"
            : "rgba(var(--theme-text-rgb), 0.25)",
        }}>
          {group.name}
        </span>
        <span style={{
          fontSize: 10, fontFamily: "monospace",
          color: "rgba(var(--theme-text-rgb), 0.3)", flexShrink: 0, marginLeft: 4,
        }}>
          {Math.round(group.opacity * 100)}%
        </span>
      </div>
    </div>
  );

  /** Compute display name with dedup suffix for the sidebar only. */
  const displayLayerName = useCallback(
    (layer: CanvasLayer): string => {
      const sameName = canvas.layers.filter((l) => l.name === layer.name);
      if (sameName.length <= 1) return layer.name;
      const idx = sameName.findIndex((l) => l.id === layer.id);
      return `${layer.name} #${idx + 1}`;
    },
    [canvas.layers],
  );

  // ── Layer row ───────────────────────────────────────────────────────

  const renderLayerRow = (layer: CanvasLayer, depth: number, idx: number) => {
    const isSelected = canvas.selectedLayerIds.includes(layer.id);
    const isActive = layer.id === canvas.activeLayerId;
    const hasMask = Array.isArray(layer.maskStrokes);
    const maskTarget = layer.maskTarget ?? "content";
    const indent = depth * 12;
    return (
      <div key={layer.id ?? `layer-${idx}`}>
        <div
          draggable
          onClick={(e) => {
            if (e.shiftKey) canvas.selectLayerRange(layer.id);
            else if (e.ctrlKey || e.metaKey)
              canvas.toggleLayerSelection(layer.id);
            else canvas.setActiveLayer(layer.id);
          }}
          onDragStart={(e) => onDragStart(layer.id, e)}
          onDragOver={(e) => onDragOver(layer.id, e)}
          onDragLeave={() => setDragOverId(null)}
          onDrop={(e) => { e.preventDefault(); setDragOverId(null); performDrop(layer.id); }}
          onDragEnd={onDragEnd}
          onContextMenu={(e) => { e.preventDefault(); setContextMenu({ x: e.clientX, y: e.clientY, layerId: layer.id }); }}
          role="button"
          style={{
            display: "flex",
            alignItems: "center",
            padding: `0 6px 0 ${4 + indent}px`,
            height: ROW_H,
            gap: 5,
            cursor: draggingId === layer.id ? "grabbing" : "default",
            background: isActive
              ? "rgba(99,153,255,0.16)"
              : isSelected
                ? "rgba(99,153,255,0.08)"
                : dragOverId === layer.id
                  ? "rgba(255,255,255,0.08)"
                  : "transparent",
            borderLeft: `2px solid ${isSelected ? "#6399ff" : "transparent"}`,
            userSelect: "none",
          }}
          onMouseEnter={(e) => {
            if (!isActive && !isSelected && dragOverId !== layer.id)
              (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.04)";
          }}
          onMouseLeave={(e) => {
            if (!isActive && !isSelected && dragOverId !== layer.id)
              (e.currentTarget as HTMLDivElement).style.background = "transparent";
          }}
        >
          {/* Visibility eye */}
          <button
            title={layer.visible ? "Hide" : "Show"}
            onClick={(e) => { e.stopPropagation(); canvas.setLayerVisible(layer.id, !layer.visible); }}
            style={{
              background: "none", border: "none", padding: 0,
              flexShrink: 0, cursor: "pointer",
              color: layer.visible ? "rgba(var(--theme-text-rgb), 0.55)" : "rgba(var(--theme-text-rgb), 0.2)",
              display: "flex", alignItems: "center",
            }}
          >
            {layer.visible ? <Eye size={13} strokeWidth={1.75} /> : <EyeOff size={13} strokeWidth={1.75} />}
          </button>

          {/* Layer content thumbnail */}
          <LayerThumbnail
            layer={layer}
            docWidth={canvas.documentWidth}
            docHeight={canvas.documentHeight}
            type="content"
            active={isActive && maskTarget === "content"}
            size={30}
            onClick={(e) => {
              e.stopPropagation();
              canvas.setActiveLayer(layer.id);
              if (hasMask) canvas.setLayerMaskTarget(layer.id, "content");
            }}
          />

          {/* Mask thumbnail — only shown when mask exists */}
          {hasMask && (
            <LayerThumbnail
              layer={layer}
              docWidth={canvas.documentWidth}
              docHeight={canvas.documentHeight}
              type="mask"
              active={isActive && maskTarget === "mask"}
              size={30}
              onClick={(e) => {
                e.stopPropagation();
                canvas.setActiveLayer(layer.id);
                canvas.setLayerMaskTarget(layer.id, "mask");
              }}
            />
          )}

          {/* Name / edit */}
          {editingId === layer.id ? (
            <input
              autoFocus value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={() => commitEdit(layer.id)}
              onKeyDown={(e) => onKeyDown(e, layer.id)}
              onClick={(e) => e.stopPropagation()}
              style={{
                flexGrow: 1, minWidth: 0, fontSize: 11,
                padding: "1px 4px",
                background: "rgba(0,0,0,0.5)",
                border: "1px solid rgba(99,153,255,0.5)",
                borderRadius: 3,
                color: "rgba(var(--theme-text-rgb), 0.9)", outline: "none",
              }}
            />
          ) : (
            <span
              style={{
                flexGrow: 1, minWidth: 0, overflow: "hidden",
                textOverflow: "ellipsis", whiteSpace: "nowrap",
                fontSize: 11,
                color: layer.visible
                  ? isActive ? "rgba(var(--theme-text-rgb), 0.9)" : "rgba(var(--theme-text-rgb), 0.65)"
                  : "rgba(var(--theme-text-rgb), 0.25)",
              }}
              onDoubleClick={(e) => { e.stopPropagation(); startEdit(layer); }}
            >
              {displayLayerName(layer)}
            </span>
          )}

          <span style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(var(--theme-text-rgb), 0.3)", flexShrink: 0 }}>
            {Math.round(layer.opacity * 100)}%
          </span>
        </div>
      </div>
    );
  };

  // ── Delete selected layers/groups ───────────────────────────────────

  const deleteSelected = useCallback(() => {
    const toDelete = canvas.selectedLayerIds.filter((id) => {
      const layer = canvas.layers.find((l) => l.id === id);
      return true;
    });
    // Delete from highest index to lowest so splice doesn't shift.
    const sorted = [...toDelete].sort(
      (a, b) =>
        canvas.layers.findIndex((l) => l.id === b) -
        canvas.layers.findIndex((l) => l.id === a),
    );
    for (const id of sorted) {
      const layer = canvas.layers.find((l) => l.id === id);
      if (layer) {
        canvas.deleteLayer(id);
      } else {
        canvas.deleteGroup(id);
      }
    }
  }, [canvas]);

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        minWidth: 0,
      }}
    >
      {/* Anchored opacity slider */}
      <OpacitySlider
        value={activeOpacity}
        onChange={handleOpacityChange}
      />

      {/* Layer list */}
      <div style={{ flexGrow: 1, overflowY: "auto", minHeight: 0 }}>
        {renderItems.map((item, idx) => {
          if (item.type === "layer") {
            return renderLayerRow(item.layer, item.depth, idx);
          }
          return renderGroupRow(item.group, idx);
        })}
      </div>

      {/* Footer — action buttons left-aligned */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          gap: 2,
          padding: "5px 8px",
          borderTop: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <IconBtn title="Add layer" onClick={() => setShowNewLayer(true)}>
          <LayersPlus size={15} strokeWidth={1.75} />
        </IconBtn>
        <IconBtn title="Add group" onClick={canvas.addLayerGroup}>
          <FolderPlus size={15} strokeWidth={1.75} />
        </IconBtn>
        <IconBtn
          title="Copy selected"
          disabled={canvas.selectedLayerIds.length === 0}
          onClick={copySelected}
        >
          <Copy size={15} strokeWidth={1.75} />
        </IconBtn>
        <span style={{ width: 4 }} />
        <IconBtn
          title="Move up"
          disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
          onClick={() =>
            canvas.activeLayerId &&
            canvas.reorderLayer(canvas.activeLayerId, "up")
          }
        >
          <ChevronUp size={15} strokeWidth={1.75} />
        </IconBtn>
        <IconBtn
          title="Move down"
          disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
          onClick={() =>
            canvas.activeLayerId &&
            canvas.reorderLayer(canvas.activeLayerId, "down")
          }
        >
          <ChevronDown size={15} strokeWidth={1.75} />
        </IconBtn>
        <IconBtn
          title="Merge selected"
          disabled={canvas.selectedLayerIds.length < 2}
          onClick={canvas.mergeSelectedLayers}
        >
          <Combine size={15} strokeWidth={1.75} />
        </IconBtn>
        {canvas.activeLayerId && (() => {
          const activeLayer = canvas.layers.find((l) => l.id === canvas.activeLayerId);
          const hasMask = Array.isArray(activeLayer?.maskStrokes);
          return (
            <IconBtn
              title={hasMask ? "Remove Layer Mask" : "Add Mask to Layer"}
              active={hasMask}
              onClick={() => {
                if (!canvas.activeLayerId) return;
                if (hasMask) {
                  canvas.removeLayerMask(canvas.activeLayerId);
                } else {
                  setShowMaskModal(true);
                }
              }}
            >
              <Drama size={15} strokeWidth={1.75} />
            </IconBtn>
          );
        })()}
        <div style={{ flex: 1 }} />
        <IconBtn
          title="Delete selected"
          danger
          disabled={canvas.selectedLayerIds.length === 0}
          onClick={deleteSelected}
        >
          <Trash2 size={15} strokeWidth={1.75} />
        </IconBtn>
      </div>
      {/* Right-click context menu */}
      {contextMenu && (() => {
        const menuLayer = canvas.layers.find((l) => l.id === contextMenu.layerId);
        const menuHasMask = Array.isArray(menuLayer?.maskStrokes);
        return (
          <div
            onMouseDown={(e) => e.stopPropagation()}
            style={{
              position: "fixed",
              top: contextMenu.y,
              left: contextMenu.x,
              zIndex: 9999,
              background: "#1e1e2e",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 6,
              padding: "4px 0",
              minWidth: 160,
              boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
            }}
          >
            {[
              {
                label: "Delete Layer",
                danger: true,
                disabled: false,
                onClick: () => { canvas.deleteLayer(contextMenu.layerId); setContextMenu(null); },
              },
              {
                label: "Delete Mask",
                danger: false,
                disabled: !menuHasMask,
                onClick: () => { if (menuHasMask) { canvas.removeLayerMask(contextMenu.layerId); } setContextMenu(null); },
              },
            ].map((item) => (
              <button
                key={item.label}
                disabled={item.disabled}
                onClick={item.onClick}
                style={{
                  display: "block",
                  width: "100%",
                  padding: "6px 14px",
                  background: "none",
                  border: "none",
                  textAlign: "left",
                  fontSize: 12,
                  cursor: item.disabled ? "default" : "pointer",
                  color: item.disabled
                    ? "rgba(255,255,255,0.2)"
                    : item.danger
                      ? "rgba(255,100,100,0.8)"
                      : "rgba(255,255,255,0.75)",
                }}
                onMouseEnter={(e) => {
                  if (!item.disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.07)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background = "none";
                }}
              >
                {item.label}
              </button>
            ))}
          </div>
        );
      })()}

      <NewLayerModal
        show={showNewLayer}
        layerIndex={canvas.layers.length + 1}
        defaultName={canvas.activeLayer?.name === "Background" ? "Layer" : (canvas.activeLayer?.name ?? "Layer")}
        onConfirm={(name, opacity, _fillColor) => { canvas.addLayer(name, opacity); }}
        onHide={() => setShowNewLayer(false)}
      />
      <NewLayerMaskModal
        show={showMaskModal}
        layerName={canvas.activeLayer?.name ?? "Layer"}
        onAdd={(fill, _invert) => {
          if (canvas.activeLayerId) {
            canvas.addLayerMask(canvas.activeLayerId, fill);
          }
          setShowMaskModal(false);
        }}
        onHide={() => setShowMaskModal(false)}
      />
    </div>
  );
}
