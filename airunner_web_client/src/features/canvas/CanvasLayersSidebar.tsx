import { useState, useCallback, useRef } from "react";
import {
  Eye, EyeOff, Plus, ChevronUp, ChevronDown, Trash2, Combine, FolderOpen, FolderClosed,
} from "lucide-react";
import { useCanvasContext } from "./CanvasContext";
import type { CanvasLayer, LayerGroup } from "./useCanvasState";
import Form from "react-bootstrap/Form";

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
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const dragSourceId = useRef<string | null>(null);

  /** Convert a display index (reversed, top-first) to internal index (bottom-first). */
  const displayToInternal = (displayIdx: number) =>
    canvas.layers.length - 1 - displayIdx;

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

  type RenderGroupItem = { type: "group"; group: LayerGroup };
  type RenderLayerItem = { type: "layer"; layer: CanvasLayer; depth: number };
  const renderItems: (RenderGroupItem | RenderLayerItem)[] = [];
  // Build interleaved list: iterate layers bottom→top (the internal order),
  // but we want to display top→first. So reverse.
  const reversedLayers = [...canvas.layers].reverse();
  // Groups in the same reversed order.
  const reversedGroups = [...canvas.layerGroups].reverse();
  const groupedIds = new Set(canvas.layers.filter((l) => l.parentGroupId).map((l) => l.id));

  // Insert group headers before their first child.
  for (const group of reversedGroups) {
    const expanded = group.expanded;
    const children = reversedLayers.filter((l) => l.parentGroupId === group.id);
    if (children.length > 0) {
      renderItems.push({ type: "group", group });
      if (expanded) {
        for (const child of children) {
          renderItems.push({ type: "layer", layer: child, depth: 1 });
        }
      }
    }
  }
  // Ungrouped layers (those not in any group).
  for (const layer of reversedLayers) {
    if (!layer.parentGroupId && !groupedIds.has(layer.id)) {
      renderItems.push({ type: "layer", layer, depth: 0 });
    }
  }

  const renderLayerRow = (layer: CanvasLayer, depth: number) => {
    const isSelected = canvas.selectedLayerIds.includes(layer.id);
    const isActive = layer.id === canvas.activeLayerId;
    const isExpanded = expandedId === layer.id;
    const indent = depth * 12;

    return (
      <div key={layer.id}>
        <div
          draggable
          onClick={(e) => {
            if (e.shiftKey) canvas.selectLayerRange(layer.id);
            else if (e.ctrlKey || e.metaKey) canvas.toggleLayerSelection(layer.id);
            else canvas.setActiveLayer(layer.id);
          }}
          onDragStart={(e) => {
            dragSourceId.current = layer.id;
            setDraggingId(layer.id);
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", layer.id);
          }}
          onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverId(layer.id); }}
          onDragLeave={() => setDragOverId(null)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverId(null);
            const srcId = dragSourceId.current;
            if (!srcId || srcId === layer.id) return;
            const internalIdx = displayToInternal(
              [...canvas.layers].reverse().findIndex((l) => l.id === layer.id),
            );
            canvas.reorderLayerToIndex(srcId, internalIdx);
            dragSourceId.current = null;
          }}
          onDragEnd={() => { setDragOverId(null); setDraggingId(null); dragSourceId.current = null; }}
          role="button"
          style={{
            display: "flex",
            alignItems: "center",
            padding: `0 6px 0 ${4 + indent}px`,
            height: 30,
            cursor: draggingId === layer.id ? "grabbing" : "default",
            background: isActive ? "rgba(99,153,255,0.16)" : isSelected ? "rgba(99,153,255,0.08)" : dragOverId === layer.id ? "rgba(255,255,255,0.08)" : "transparent",
            borderLeft: `2px solid ${isSelected ? "#6399ff" : "transparent"}`,
            userSelect: "none",
          }}
          onMouseEnter={(e) => { if (!isActive && !isSelected && dragOverId !== layer.id) (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.04)"; }}
          onMouseLeave={(e) => { if (!isActive && !isSelected && dragOverId !== layer.id) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
        >
          <button
            title={layer.visible ? "Hide" : "Show"}
            onClick={(e) => { e.stopPropagation(); canvas.setLayerVisible(layer.id, !layer.visible); }}
            style={{ background: "none", border: "none", padding: 0, marginRight: 4, flexShrink: 0, cursor: "pointer", color: layer.visible ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.2)", display: "flex", alignItems: "center" }}
          >
            {layer.visible ? <Eye size={13} strokeWidth={1.75} /> : <EyeOff size={13} strokeWidth={1.75} />}
          </button>

          {editingId === layer.id ? (
            <input
              autoFocus value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={() => commitEdit(layer.id)}
              onKeyDown={(e) => onKeyDown(e, layer.id)}
              onClick={(e) => e.stopPropagation()}
              style={{ flexGrow: 1, minWidth: 0, fontSize: 12, padding: "1px 4px", background: "rgba(0,0,0,0.5)", border: "1px solid rgba(99,153,255,0.5)", borderRadius: 3, color: "rgba(255,255,255,0.9)", outline: "none" }}
            />
          ) : (
            <span
              style={{ flexGrow: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12, color: layer.visible ? (isActive ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.65)") : "rgba(255,255,255,0.25)", cursor: "default" }}
              onDoubleClick={(e) => { e.stopPropagation(); startEdit(layer); }}
            >
              {layer.name}
            </span>
          )}

          <span
            title="Click to expand opacity"
            onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : layer.id); }}
            style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(255,255,255,0.3)", flexShrink: 0, marginLeft: 4, cursor: "pointer" }}
          >
            {Math.round(layer.opacity * 100)}%
          </span>
        </div>

        {isExpanded && (
          <div style={{ padding: "4px 10px 6px 18px", background: "rgba(99,153,255,0.06)", borderBottom: "1px solid rgba(255,255,255,0.05)" }} onClick={(e) => e.stopPropagation()}>
            <Form.Range min={0} max={1} step={0.01} value={layer.opacity} onChange={(e) => canvas.setLayerOpacity(layer.id, Number(e.target.value))} style={{ marginBottom: 0 }} />
          </div>
        )}
      </div>
    );
  };

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
      {/* Header — title only, no buttons */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "6px 8px 5px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)" }}>
          Layers
        </span>
      </div>

      {/* Layer list — fills middle space */}
      <div style={{ flexGrow: 1, overflowY: "auto", minHeight: 0 }}>
        {renderItems.map((item) => {
          if (item.type === "layer") return renderLayerRow(item.layer, item.depth);

          // Group header row
          const group = item.group;
          const gExpanded = group.expanded;
          return (
            <div key={group.id}>
              <div
                draggable
                onClick={() => canvas.toggleGroupExpanded(group.id)}
                onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setDragOverId(group.id); }}
                onDragLeave={() => setDragOverId(null)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOverId(null);
                  const srcId = dragSourceId.current;
                  if (!srcId) return;
                  canvas.moveLayerToGroup(srcId, group.id);
                  dragSourceId.current = null;
                }}
                onDragEnd={() => { setDragOverId(null); setDraggingId(null); dragSourceId.current = null; }}
                role="button"
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "0 6px 0 4px",
                  height: 28,
                  cursor: "default",
                  background: dragOverId === group.id ? "rgba(99,153,255,0.12)" : "rgba(255,255,255,0.03)",
                  userSelect: "none",
                }}
              >
                {gExpanded ? <FolderOpen size={12} strokeWidth={1.75} style={{ marginRight: 4, flexShrink: 0, color: "rgba(255,255,255,0.4)" }} />
                  : <FolderClosed size={12} strokeWidth={1.75} style={{ marginRight: 4, flexShrink: 0, color: "rgba(255,255,255,0.4)" }} />}
                <span style={{ flexGrow: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.5)" }}>
                  {group.name}
                </span>
                <button
                  title="Delete group"
                  onClick={(e) => { e.stopPropagation(); canvas.deleteGroup(group.id); }}
                  style={{ background: "none", border: "none", padding: 0, marginLeft: 4, flexShrink: 0, cursor: "pointer", color: "rgba(255,100,100,0.5)", display: "flex", alignItems: "center" }}
                >
                  <Trash2 size={10} strokeWidth={1.75} />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer — action buttons anchored at bottom */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 2,
          padding: "5px 8px",
          borderTop: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <IconBtn title="Add layer" onClick={canvas.addLayer}>
          <Plus size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn title="Add group" onClick={canvas.addLayerGroup}>
          <FolderClosed size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Move up"
          disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
          onClick={() => canvas.activeLayerId && canvas.reorderLayer(canvas.activeLayerId, "up")}
        >
          <ChevronUp size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Move down"
          disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
          onClick={() => canvas.activeLayerId && canvas.reorderLayer(canvas.activeLayerId, "down")}
        >
          <ChevronDown size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Merge selected"
          disabled={canvas.selectedLayerIds.length < 1}
          onClick={canvas.mergeSelectedLayers}
        >
          <Combine size={13} strokeWidth={2} />
        </IconBtn>
        <IconBtn
          title="Delete layer(s)"
          danger
          disabled={canvas.selectedLayerIds.length === 0 || canvas.layers.length <= canvas.selectedLayerIds.length}
          onClick={() => {
            // Delete all selected layers in reverse order (bottom-up) to
            // keep indices stable, then fall back to the first remaining.
            const toDelete = canvas.selectedLayerIds.filter(
              (id) => canvas.layers.length > 1,
            );
            // Delete from highest index to lowest so splice doesn't shift.
            const sorted = [...toDelete].sort(
              (a, b) =>
                canvas.layers.findIndex((l) => l.id === b) -
                canvas.layers.findIndex((l) => l.id === a),
            );
            for (const id of sorted) {
              if (canvas.layers.length > 1) canvas.deleteLayer(id);
            }
          }}
        >
          <Trash2 size={13} strokeWidth={2} />
        </IconBtn>
      </div>
    </div>
  );
}
