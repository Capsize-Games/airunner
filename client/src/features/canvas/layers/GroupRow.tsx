import { Eye, EyeOff, SquareMinus, SquarePlus } from "lucide-react";
import { useCanvasContext } from "../CanvasContext";
import type { LayerGroup } from "../useCanvasState";

interface DragProps {
  dragOverId: string | null;
  dragPosition: "above" | "below";
  dragSourceId: React.MutableRefObject<string | null>;
  onDragStart: (id: string, e: React.DragEvent) => void;
  onDragOver: (id: string, e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDragEnd: () => void;
  onClearDrag: () => void;
}

interface Props {
  group: LayerGroup;
  drag: DragProps;
}

export default function GroupRow({ group, drag }: Props) {
  const canvas = useCanvasContext();
  const isDragOver = drag.dragOverId === group.id;
  const dropAbove = isDragOver && drag.dragPosition === "above";
  const dropBelow = isDragOver && drag.dragPosition === "below";

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    drag.onClearDrag();
    const srcId = drag.dragSourceId.current;
    if (!srcId) return;
    let orderIdx = canvas.displayOrder.indexOf(group.id);
    if (drag.dragPosition === "above") orderIdx += 1;
    const isLayer = canvas.layers.some((l) => l.id === srcId);
    if (isLayer) {
      canvas.moveLayerToGroup(srcId, group.id, orderIdx);
    } else {
      canvas.reorderDisplayItem(srcId, orderIdx);
    }
    drag.dragSourceId.current = null;
  };

  return (
    <div>
      {dropAbove && <div style={{ height: 2, background: "#6399ff", margin: "0 4px" }} />}
      <div
        draggable
        onClick={() => canvas.toggleGroupExpanded(group.id)}
        onDragStart={(e) => drag.onDragStart(group.id, e)}
        onDragOver={(e) => drag.onDragOver(group.id, e)}
        onDragLeave={drag.onDragLeave}
        onDrop={handleDrop}
        onDragEnd={drag.onDragEnd}
        role="button"
        style={{
          display: "flex",
          alignItems: "center",
          padding: "0 6px 0 4px",
          height: 28,
          cursor: "default",
          background: isDragOver ? "rgba(99,153,255,0.12)" : "rgba(255,255,255,0.03)",
          userSelect: "none",
        }}
      >
        <button
          title={group.visible ? "Hide group" : "Show group"}
          onClick={(e) => { e.stopPropagation(); canvas.setGroupVisible(group.id, !group.visible); }}
          style={{
            background: "none", border: "none", padding: 0,
            marginRight: 4, flexShrink: 0, cursor: "pointer",
            color: group.visible ? "rgba(var(--theme-text-rgb), 0.55)" : "rgba(var(--theme-text-rgb), 0.2)",
            display: "flex", alignItems: "center",
            borderRadius: 3, transition: "background 0.1s, color 0.1s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.08)";
            e.currentTarget.style.color = "rgba(var(--theme-text-rgb), 0.85)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "none";
            e.currentTarget.style.color = group.visible
              ? "rgba(var(--theme-text-rgb), 0.55)"
              : "rgba(var(--theme-text-rgb), 0.2)";
          }}
        >
          {group.visible ? <Eye size={13} strokeWidth={1.75} /> : <EyeOff size={13} strokeWidth={1.75} />}
        </button>

        {group.expanded ? (
          <SquareMinus size={12} strokeWidth={1.75}
            style={{ marginRight: 4, flexShrink: 0, color: "rgba(var(--theme-text-rgb), 0.4)" }}
          />
        ) : (
          <SquarePlus size={12} strokeWidth={1.75}
            style={{ marginRight: 4, flexShrink: 0, color: "rgba(var(--theme-text-rgb), 0.4)" }}
          />
        )}

        <span style={{
          flexGrow: 1, minWidth: 0, overflow: "hidden",
          textOverflow: "ellipsis", whiteSpace: "nowrap",
          fontSize: 11, fontWeight: 600,
          color: group.visible ? "rgba(var(--theme-text-rgb), 0.5)" : "rgba(var(--theme-text-rgb), 0.25)",
        }}>
          {group.name}
        </span>
        <span className="text-mono-stat flex-shrink-0" style={{ marginLeft: 4 }}>
          {Math.round(group.opacity * 100)}%
        </span>
      </div>
      {dropBelow && <div style={{ height: 2, background: "#6399ff", margin: "0 4px" }} />}
    </div>
  );
}
