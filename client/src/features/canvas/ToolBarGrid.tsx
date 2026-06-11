import { Grid3x3, Magnet, Lock, Unlock } from "lucide-react";
import { IconBtn } from "./ToolBarTools";
import type { ActiveGridArea } from "./useCanvasState";

interface ToolBarGridProps {
  showGrid: boolean;
  snapToGrid: boolean;
  activeGridArea: ActiveGridArea;
  gridLocked: boolean;
  onToggleGrid: () => void;
  onToggleSnap: () => void;
  onSetGridArea: (area: ActiveGridArea) => void;
  onToggleGridLock: () => void;
}

const gridInputStyle: React.CSSProperties = {
  width: 52,
  background: "rgba(0,0,0,0.4)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 4,
  color: "rgba(var(--theme-text-rgb), 0.8)",
  fontSize: 11,
  textAlign: "center",
  padding: "2px 0",
};

/**
 * Grid visibility, snapping, and active-grid-area controls for the toolbar.
 */
export default function ToolBarGrid({
  showGrid,
  snapToGrid,
  activeGridArea,
  gridLocked,
  onToggleGrid,
  onToggleSnap,
  onSetGridArea,
  onToggleGridLock,
}: ToolBarGridProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        gap: 3,
        flexShrink: 0,
      }}
    >
      <IconBtn
        title="Toggle grid" active={showGrid} onClick={onToggleGrid}
      >
        <Grid3x3 size={15} strokeWidth={1.75} />
      </IconBtn>
      <IconBtn
        title="Snap to grid" active={snapToGrid} onClick={onToggleSnap}
      >
        <Magnet size={15} strokeWidth={1.75} />
      </IconBtn>
      <span style={{
        fontSize: 10, color: "rgba(var(--theme-text-rgb), 0.35)",
        whiteSpace: "nowrap",
      }}>
        Grid
      </span>
      <div className="d-flex align-items-center" style={{ gap: 3 }}>
        <span style={{ fontSize: 10, color: "rgba(var(--theme-text-rgb), 0.4)" }}>
          W
        </span>
        <input
          type="number"
          value={activeGridArea.width}
          onChange={(e) => {
            const w = Number(e.target.value);
            const h = gridLocked ? w : activeGridArea.height;
            onSetGridArea({ ...activeGridArea, width: w, height: h });
          }}
          onBlur={(e) => {
            const w = Math.max(8, Math.round(Number(e.target.value) / 8) * 8);
            const h = gridLocked ? w : activeGridArea.height;
            onSetGridArea({ ...activeGridArea, width: w, height: h });
          }}
          style={gridInputStyle}
          title="Grid area width"
        />
        <IconBtn
          title={
            gridLocked
              ? "Unlock aspect ratio"
              : "Lock aspect ratio"
          }
          active={gridLocked}
          onClick={onToggleGridLock}
        >
          {gridLocked
            ? <Lock size={13} strokeWidth={1.75} />
            : <Unlock size={13} strokeWidth={1.75} />}
        </IconBtn>
        <span style={{ fontSize: 10, color: "rgba(var(--theme-text-rgb), 0.4)" }}>
          H
        </span>
        <input
          type="number"
          value={activeGridArea.height}
          onChange={(e) => {
            const h = Number(e.target.value);
            const w = gridLocked ? h : activeGridArea.width;
            onSetGridArea({ ...activeGridArea, width: w, height: h });
          }}
          onBlur={(e) => {
            const h = Math.max(8, Math.round(Number(e.target.value) / 8) * 8);
            const w = gridLocked ? h : activeGridArea.width;
            onSetGridArea({ ...activeGridArea, width: w, height: h });
          }}
          style={gridInputStyle}
          title="Grid area height"
        />
      </div>
    </div>
  );
}
