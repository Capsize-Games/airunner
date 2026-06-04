import { useState, useCallback } from "react";
import {
  Eye, EyeOff, Plus, ChevronUp, ChevronDown, Trash2,
} from "lucide-react";
import { useCanvasContext } from "./CanvasContext";
import type { CanvasLayer } from "./useCanvasState";
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

  const displayLayers = [...canvas.layers].reverse();

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
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "6px 8px 5px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.07em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)" }}>
          Layers
        </span>
        <div style={{ display: "flex", gap: 2 }}>
          <IconBtn title="Add layer" onClick={canvas.addLayer}>
            <Plus size={13} strokeWidth={2} />
          </IconBtn>
          <IconBtn
            title="Move up"
            disabled={!canvas.activeLayerId}
            onClick={() => canvas.activeLayerId && canvas.reorderLayer(canvas.activeLayerId, "up")}
          >
            <ChevronUp size={13} strokeWidth={2} />
          </IconBtn>
          <IconBtn
            title="Move down"
            disabled={!canvas.activeLayerId}
            onClick={() => canvas.activeLayerId && canvas.reorderLayer(canvas.activeLayerId, "down")}
          >
            <ChevronDown size={13} strokeWidth={2} />
          </IconBtn>
          <IconBtn
            title="Delete layer"
            danger
            disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
            onClick={() => canvas.activeLayerId && canvas.deleteLayer(canvas.activeLayerId)}
          >
            <Trash2 size={13} strokeWidth={2} />
          </IconBtn>
        </div>
      </div>

      {/* Layer list */}
      <div style={{ flexGrow: 1, overflowY: "auto", minHeight: 0 }}>
        {displayLayers.map((layer) => {
          const isActive = layer.id === canvas.activeLayerId;
          const isExpanded = expandedId === layer.id;

          return (
            <div key={layer.id}>
              {/* Layer row */}
              <div
                onClick={() => canvas.setActiveLayer(layer.id)}
                role="button"
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "0 6px 0 4px",
                  height: 30,
                  cursor: "pointer",
                  background: isActive ? "rgba(99,153,255,0.16)" : "transparent",
                  borderLeft: `2px solid ${isActive ? "#6399ff" : "transparent"}`,
                  userSelect: "none",
                }}
                onMouseEnter={(e) => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.04)"; }}
                onMouseLeave={(e) => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
              >
                {/* Visibility */}
                <button
                  title={layer.visible ? "Hide" : "Show"}
                  onClick={(e) => { e.stopPropagation(); canvas.setLayerVisible(layer.id, !layer.visible); }}
                  style={{ background: "none", border: "none", padding: 0, marginRight: 4, flexShrink: 0, cursor: "pointer", color: layer.visible ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.2)", display: "flex", alignItems: "center" }}
                >
                  {layer.visible ? <Eye size={13} strokeWidth={1.75} /> : <EyeOff size={13} strokeWidth={1.75} />}
                </button>

                {/* Name */}
                {editingId === layer.id ? (
                  <input
                    autoFocus
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => commitEdit(layer.id)}
                    onKeyDown={(e) => onKeyDown(e, layer.id)}
                    onClick={(e) => e.stopPropagation()}
                    style={{ flexGrow: 1, minWidth: 0, fontSize: 12, padding: "1px 4px", background: "rgba(0,0,0,0.5)", border: "1px solid rgba(99,153,255,0.5)", borderRadius: 3, color: "rgba(255,255,255,0.9)", outline: "none" }}
                  />
                ) : (
                  <span
                    style={{ flexGrow: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12, color: layer.visible ? (isActive ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.65)") : "rgba(255,255,255,0.25)", cursor: "text" }}
                    onDoubleClick={(e) => { e.stopPropagation(); startEdit(layer); }}
                  >
                    {layer.name}
                  </span>
                )}

                {/* Opacity badge */}
                <span
                  title="Click to expand opacity"
                  onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : layer.id); }}
                  style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(255,255,255,0.3)", flexShrink: 0, marginLeft: 4, cursor: "pointer" }}
                >
                  {Math.round(layer.opacity * 100)}%
                </span>
              </div>

              {/* Expanded opacity slider */}
              {isExpanded && (
                <div
                  style={{ padding: "4px 10px 6px", background: "rgba(99,153,255,0.06)", borderBottom: "1px solid rgba(255,255,255,0.05)" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <Form.Range
                    min={0} max={1} step={0.01}
                    value={layer.opacity}
                    onChange={(e) => canvas.setLayerOpacity(layer.id, Number(e.target.value))}
                    style={{ marginBottom: 0 }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
