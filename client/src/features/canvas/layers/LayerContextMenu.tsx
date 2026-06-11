import { useCanvasContext } from "../CanvasContext";

interface Props {
  contextMenu: { x: number; y: number; layerId: string } | null;
  onClose: () => void;
}

export default function LayerContextMenu({ contextMenu, onClose }: Props) {
  const canvas = useCanvasContext();

  if (!contextMenu) return null;

  const isGroup = canvas.layerGroups.some((g) => g.id === contextMenu.layerId);
  const menuLayer = canvas.layers.find((l) => l.id === contextMenu.layerId);
  const hasMask = Array.isArray(menuLayer?.maskStrokes);

  const items = isGroup
    ? [
        {
          label: "Rename Group",
          danger: false,
          disabled: false,
          onClick: () => {
            const g = canvas.layerGroups.find((g) => g.id === contextMenu.layerId);
            if (g) canvas.renameGroup(contextMenu.layerId, prompt("Group name:", g.name) ?? g.name);
            onClose();
          },
        },
        {
          label: "Delete Group",
          danger: true,
          disabled: false,
          onClick: () => { canvas.deleteGroup(contextMenu.layerId); onClose(); },
        },
      ]
    : [
        {
          label: "Delete Layer",
          danger: true,
          disabled: false,
          onClick: () => { canvas.deleteLayer(contextMenu.layerId); onClose(); },
        },
        {
          label: "Delete Mask",
          danger: false,
          disabled: !hasMask,
          onClick: () => { if (hasMask) canvas.removeLayerMask(contextMenu.layerId); onClose(); },
        },
      ];

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
      {items.map((item) => (
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
            if (!item.disabled)
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.07)";
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
}
