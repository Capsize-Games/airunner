import {
  ChevronUp, ChevronDown, Trash2, Combine,
  FolderPlus, Copy, LayersPlus, Drama,
} from "lucide-react";
import { useCanvasContext } from "../CanvasContext";
import IconBtn from "../IconBtn";

interface Props {
  onAddLayer: () => void;
  onAddMask: () => void;
  onCopySelected: () => void;
  onDeleteSelected: () => void;
}

export default function LayerFooter({
  onAddLayer, onAddMask, onCopySelected, onDeleteSelected,
}: Props) {
  const canvas = useCanvasContext();
  const activeLayer = canvas.layers.find((l) => l.id === canvas.activeLayerId);
  const hasMask = Array.isArray(activeLayer?.maskStrokes);

  return (
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
      <IconBtn title="Add layer" onClick={onAddLayer}>
        <LayersPlus size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn title="Add group" onClick={canvas.addLayerGroup}>
        <FolderPlus size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn
        title="Copy selected"
        disabled={canvas.selectedLayerIds.length === 0}
        onClick={onCopySelected}
      >
        <Copy size={15} strokeWidth={1.75} />
      </IconBtn>

      <span style={{ width: 4 }} />

      <IconBtn
        title="Move up"
        disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
        onClick={() => canvas.activeLayerId && canvas.reorderLayer(canvas.activeLayerId, "up")}
      >
        <ChevronUp size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn
        title="Move down"
        disabled={!canvas.activeLayerId || canvas.layers.length <= 1}
        onClick={() => canvas.activeLayerId && canvas.reorderLayer(canvas.activeLayerId, "down")}
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

      {canvas.activeLayerId && (
        <IconBtn
          title={hasMask ? "Remove Layer Mask" : "Add Mask to Layer"}
          active={hasMask}
          onClick={() => {
            if (!canvas.activeLayerId) return;
            if (hasMask) canvas.removeLayerMask(canvas.activeLayerId);
            else onAddMask();
          }}
        >
          <Drama size={15} strokeWidth={1.75} />
        </IconBtn>
      )}

      <div style={{ flex: 1 }} />

      <IconBtn
        title="Delete selected"
        danger
        disabled={canvas.selectedLayerIds.length === 0}
        onClick={onDeleteSelected}
      >
        <Trash2 size={15} strokeWidth={1.75} />
      </IconBtn>
    </div>
  );
}
