import { Eye, EyeOff } from "lucide-react";
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
          }}
        >
          {group.visible ? <Eye size={13} strokeWidth={1.75} /> : <EyeOff size={13} strokeWidth={1.75} />}
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
          color: group.visible ? "rgba(var(--theme-text-rgb), 0.5)" : "rgba(var(--theme-text-rgb), 0.25)",
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
      {dropBelow && <div style={{ height: 2, background: "#6399ff", margin: "0 4px" }} />}
    </div>
  );
}
