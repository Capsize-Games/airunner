import { Eye, EyeOff } from "lucide-react";
import { useCanvasContext } from "../CanvasContext";
import type { CanvasLayer } from "../useCanvasState";
import LayerThumbnail from "../LayerThumbnail";

const ROW_H = 42;

export interface DragState {
  draggingId: string | null;
  dragOverId: string | null;
  dragPosition: "above" | "below";
  onDragStart: (id: string, e: React.DragEvent) => void;
  onDragOver: (id: string, e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: () => void;
  onDragEnd: () => void;
}

export interface EditState {
  editingId: string | null;
  editName: string;
  onNameChange: (v: string) => void;
  onCommit: (id: string) => void;
  onKeyDown: (e: React.KeyboardEvent, id: string) => void;
  onStart: (layer: CanvasLayer) => void;
}

interface Props {
  layer: CanvasLayer;
  depth: number;
  isActive: boolean;
  isSelected: boolean;
  displayName: string;
  drag: DragState;
  edit: EditState;
  onContextMenu: (x: number, y: number, id: string) => void;
}

export default function LayerRow({
  layer, depth, isActive, isSelected, displayName, drag, edit, onContextMenu,
}: Props) {
  const canvas = useCanvasContext();
  const hasMask = Array.isArray(layer.maskStrokes);
  const maskTarget = layer.maskTarget ?? "content";
  const indent = depth * 12;
  const isDragOver = drag.dragOverId === layer.id;
  const dropAbove = isDragOver && drag.dragPosition === "above";
  const dropBelow = isDragOver && drag.dragPosition === "below";

  return (
    <div>
      {dropAbove && <div style={{ height: 2, background: "#6399ff", margin: "0 4px" }} />}
      <div
        draggable
        onClick={(e) => {
          if (e.shiftKey) canvas.selectLayerRange(layer.id);
          else if (e.ctrlKey || e.metaKey) canvas.toggleLayerSelection(layer.id);
          else canvas.setActiveLayer(layer.id);
        }}
        onDragStart={(e) => drag.onDragStart(layer.id, e)}
        onDragOver={(e) => drag.onDragOver(layer.id, e)}
        onDragLeave={drag.onDragLeave}
        onDrop={(e) => { e.preventDefault(); drag.onDrop(); }}
        onDragEnd={drag.onDragEnd}
        onContextMenu={(e) => { e.preventDefault(); onContextMenu(e.clientX, e.clientY, layer.id); }}
        role="button"
        style={{
          display: "flex",
          alignItems: "center",
          padding: `0 6px 0 ${4 + indent}px`,
          height: ROW_H,
          gap: 5,
          cursor: drag.draggingId === layer.id ? "grabbing" : "default",
          background: isActive
            ? "rgba(99,153,255,0.16)"
            : isSelected
              ? "rgba(99,153,255,0.08)"
              : isDragOver
                ? "rgba(255,255,255,0.06)"
                : "transparent",
          borderLeft: `2px solid ${isSelected ? "#6399ff" : "transparent"}`,
          userSelect: "none",
        }}
        onMouseEnter={(e) => {
          if (!isActive && !isSelected && drag.dragOverId !== layer.id)
            (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.04)";
        }}
        onMouseLeave={(e) => {
          if (!isActive && !isSelected && drag.dragOverId !== layer.id)
            (e.currentTarget as HTMLDivElement).style.background = "transparent";
        }}
      >
        <button
          title={layer.visible ? "Hide" : "Show"}
          onClick={(e) => { e.stopPropagation(); canvas.setLayerVisible(layer.id, !layer.visible); }}
          style={{
            background: "none", border: "none", padding: 0,
            flexShrink: 0, cursor: "pointer",
            color: layer.visible ? "rgba(var(--theme-text-rgb), 0.55)" : "rgba(var(--theme-text-rgb), 0.2)",
            display: "flex", alignItems: "center",
            borderRadius: 3, transition: "background 0.1s, color 0.1s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.08)";
            e.currentTarget.style.color = "rgba(var(--theme-text-rgb), 0.85)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "none";
            e.currentTarget.style.color = layer.visible
              ? "rgba(var(--theme-text-rgb), 0.55)"
              : "rgba(var(--theme-text-rgb), 0.2)";
          }}
        >
          {layer.visible ? <Eye size={13} strokeWidth={1.75} /> : <EyeOff size={13} strokeWidth={1.75} />}
        </button>

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

        {edit.editingId === layer.id ? (
          <input
            autoFocus
            value={edit.editName}
            onChange={(e) => edit.onNameChange(e.target.value)}
            onBlur={() => edit.onCommit(layer.id)}
            onKeyDown={(e) => edit.onKeyDown(e, layer.id)}
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
            onDoubleClick={(e) => { e.stopPropagation(); edit.onStart(layer); }}
          >
            {displayName}
          </span>
        )}

        <span className="text-mono-stat flex-shrink-0">
          {Math.round(layer.opacity * 100)}%
        </span>
      </div>
      {dropBelow && <div style={{ height: 2, background: "#6399ff", margin: "0 4px" }} />}
    </div>
  );
}
