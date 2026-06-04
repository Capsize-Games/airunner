import { useState, useCallback, useRef } from "react";
import {
  Eye, EyeOff, ChevronUp, ChevronDown, Trash2, Combine,
  FolderPlus, Copy, FilePlus,
} from "lucide-react";
import { useCanvasContext } from "./CanvasContext";
import type { CanvasLayer, LayerGroup } from "./useCanvasState";
import Form from "react-bootstrap/Form";
import NewLayerModal from "./NewLayerModal";

function IconBtn({
  title,
  disabled,
  danger,
  onClick,
  children,
}: {
  title: string;
  disabled?: boolean;
  danger?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      title={title}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: 22, height: 22, padding: 0, flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        border: "none", borderRadius: 4, background: "transparent",
        color: disabled ? "rgba(255,255,255,0.15)"
          : danger ? "rgba(255,100,100,0.65)"
          : "rgba(255,255,255,0.5)",
        cursor: disabled ? "default" : "pointer",
      }}
    >
      {children}
    </button>
  );
}

export default function CanvasLayersSidebar() {
  const canvas = useCanvasContext();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName]   = useState("");
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [showNewLayer, setShowNewLayer] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const dragSourceId = useRef<string | null>(null);

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

  const renderGroupRow = (group: LayerGroup) => (
    <div key={group.id}>
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
              ? "rgba(255,255,255,0.55)"
              : "rgba(255,255,255,0.2)",
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
            style={{ marginRight: 4, flexShrink: 0, color: "rgba(255,255,255,0.4)" }}
          >
            <path d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
              fill="none" stroke="currentColor" strokeWidth={1.75} />
            <path d="M9 12h6" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width={12} height={12}
            style={{ marginRight: 4, flexShrink: 0, color: "rgba(255,255,255,0.4)" }}
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
            ? "rgba(255,255,255,0.5)"
            : "rgba(255,255,255,0.25)",
        }}>
          {group.name}
        </span>
        <span style={{
          fontSize: 10, fontFamily: "monospace",
          color: "rgba(255,255,255,0.3)", flexShrink: 0, marginLeft: 4,
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

  const renderLayerRow = (layer: CanvasLayer, depth: number) => {
    const isSelected = canvas.selectedLayerIds.includes(layer.id);
    const isActive = layer.id === canvas.activeLayerId;
    const indent = depth * 12;
    return (
      <div key={layer.id}>
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
          onDrop={(e) => {
            e.preventDefault();
            setDragOverId(null);
            performDrop(layer.id);
          }}
          onDragEnd={onDragEnd}
          role="button"
          style={{
            display: "flex",
            alignItems: "center",
            padding: `0 6px 0 ${4 + indent}px`,
            height: 30,
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
              (e.currentTarget as HTMLDivElement).style.background =
                "rgba(255,255,255,0.04)";
          }}
          onMouseLeave={(e) => {
            if (!isActive && !isSelected && dragOverId !== layer.id)
              (e.currentTarget as HTMLDivElement).style.background =
                "transparent";
          }}
        >
          <button
            title={layer.visible ? "Hide" : "Show"}
            onClick={(e) => {
              e.stopPropagation();
              canvas.setLayerVisible(layer.id, !layer.visible);
            }}
            style={{
              background: "none", border: "none", padding: 0,
              marginRight: 4, flexShrink: 0, cursor: "pointer",
              color: layer.visible
                ? "rgba(255,255,255,0.55)"
                : "rgba(255,255,255,0.2)",
              display: "flex", alignItems: "center",
            }}
          >
            {layer.visible ? (
              <Eye size={13} strokeWidth={1.75} />
            ) : (
              <EyeOff size={13} strokeWidth={1.75} />
            )}
          </button>

          {editingId === layer.id ? (
            <input
              autoFocus value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={() => commitEdit(layer.id)}
              onKeyDown={(e) => onKeyDown(e, layer.id)}
              onClick={(e) => e.stopPropagation()}
              style={{
                flexGrow: 1, minWidth: 0, fontSize: 12,
                padding: "1px 4px",
                background: "rgba(0,0,0,0.5)",
                border: "1px solid rgba(99,153,255,0.5)",
                borderRadius: 3,
                color: "rgba(255,255,255,0.9)", outline: "none",
              }}
            />
          ) : (
            <span
              style={{
                flexGrow: 1, minWidth: 0, overflow: "hidden",
                textOverflow: "ellipsis", whiteSpace: "nowrap",
                fontSize: 12,
                color: layer.visible
                  ? isActive
                    ? "rgba(255,255,255,0.9)"
                    : "rgba(255,255,255,0.65)"
                  : "rgba(255,255,255,0.25)",
                cursor: "default",
              }}
              onDoubleClick={(e) => {
                e.stopPropagation();
                startEdit(layer);
              }}
            >
              {displayLayerName(layer)}
            </span>
          )}

          <span style={{
            fontSize: 10, fontFamily: "monospace",
            color: "rgba(255,255,255,0.3)",
            flexShrink: 0, marginLeft: 4,
          }}>
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
        width: 200,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        background: "#181824",
        borderLeft: "1px solid rgba(255,255,255,0.07)",
        overflow: "hidden",
      }}
    >
      {/* Header — title */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "6px 8px 5px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <span style={{
          fontSize: 10, fontWeight: 600, letterSpacing: "0.07em",
          textTransform: "uppercase", color: "rgba(255,255,255,0.3)",
        }}>
          Layers
        </span>
      </div>

      {/* Anchored opacity slider */}
      <div
        style={{
          padding: "4px 8px 6px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <div style={{
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <span style={{
            fontSize: 10, fontFamily: "monospace",
            color: "rgba(255,255,255,0.35)", flexShrink: 0, width: 28,
            textAlign: "right",
          }}>
            {Math.round(activeOpacity * 100)}%
          </span>
          <Form.Range
            min={0} max={1} step={0.01}
            value={activeOpacity}
            onChange={(e) =>
              handleOpacityChange(Number(e.target.value))
            }
            style={{ marginBottom: 0, flexGrow: 1 }}
          />
        </div>
      </div>

      {/* Layer list */}
      <div style={{ flexGrow: 1, overflowY: "auto", minHeight: 0 }}>
        {renderItems.map((item) => {
          if (item.type === "layer") {
            return renderLayerRow(item.layer, item.depth);
          }
          return renderGroupRow(item.group);
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
          <FilePlus size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn title="Add group" onClick={canvas.addLayerGroup}>
          <FolderPlus size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Copy selected"
          disabled={canvas.selectedLayerIds.length === 0}
          onClick={copySelected}
        >
          <Copy size={13} strokeWidth={2} />
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
          <ChevronUp size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Move down"
          disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
          onClick={() =>
            canvas.activeLayerId &&
            canvas.reorderLayer(canvas.activeLayerId, "down")
          }
        >
          <ChevronDown size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Merge selected"
          disabled={canvas.selectedLayerIds.length < 2}
          onClick={canvas.mergeSelectedLayers}
        >
          <Combine size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Delete selected"
          danger
          disabled={canvas.selectedLayerIds.length === 0}
          onClick={deleteSelected}
        >
          <Trash2 size={13} strokeWidth={2} />
        </IconBtn>
      </div>
      <NewLayerModal
        show={showNewLayer}
        layerIndex={canvas.layers.length + 1}
        defaultName={canvas.activeLayer?.name === "Background" ? "Layer" : (canvas.activeLayer?.name ?? "Layer")}
        onConfirm={(name, opacity, fillColor) => {
          canvas.addLayer(name, opacity);
        }}
        onHide={() => setShowNewLayer(false)}
      />
    </div>
  );
}
