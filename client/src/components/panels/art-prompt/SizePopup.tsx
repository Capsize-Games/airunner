import { createPortal } from "react-dom";
import { saveToStorage } from "../art-model/ArtModelStorage";

interface SizePopupProps {
  anchor: { left: number; bottom: number } | null;
  portalId: string;
  genWidth: number;
  genHeight: number;
  onWidthChange: (v: number) => void;
  onHeightChange: (v: number) => void;
  persistGen: (updates: Record<string, unknown>) => void;
}

export default function SizePopup({
  anchor,
  portalId,
  genWidth,
  genHeight,
  onWidthChange,
  onHeightChange,
  persistGen,
}: SizePopupProps) {
  if (!anchor) return null;

  return createPortal(
    <div
      id={portalId}
      className="d-flex flex-column bg-theme-panel"
      style={{
        position: "fixed",
        left: anchor.left,
        bottom: anchor.bottom,
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 6,
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
        padding: "10px 12px",
        gap: 8,
        zIndex: 1300,
      }}
    >
      <div
        style={{
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          color: "var(--theme-text-secondary)",
          opacity: 0.6,
          marginBottom: 6,
        }}
      >
        Image Size
      </div>
      <div className="d-flex align-items-center" style={{ gap: 6 }}>
        <span
          style={{
            fontSize: 9,
            color: "var(--theme-text-secondary)",
            width: 10,
            flexShrink: 0,
          }}
        >
          W
        </span>
        <input
          type="number"
          className="art-no-spin"
          value={genWidth}
          onChange={(e) => onWidthChange(Number(e.target.value))}
          onBlur={(e) => {
            const v = Math.max(
              64,
              Math.min(2048, Number(e.target.value)),
            );
            onWidthChange(v);
            saveToStorage("gen_width", v);
            persistGen({ width: v });
          }}
          style={{
            height: 22,
            background: "var(--theme-input-bg)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 4,
            color: "var(--theme-text)",
            fontSize: 10,
            textAlign: "center",
            padding: "0 2px",
            width: 56,
          }}
        />
      </div>
      <div className="d-flex align-items-center" style={{ gap: 6 }}>
        <span
          style={{
            fontSize: 9,
            color: "var(--theme-text-secondary)",
            width: 10,
            flexShrink: 0,
          }}
        >
          H
        </span>
        <input
          type="number"
          className="art-no-spin"
          value={genHeight}
          onChange={(e) => onHeightChange(Number(e.target.value))}
          onBlur={(e) => {
            const v = Math.max(
              64,
              Math.min(2048, Number(e.target.value)),
            );
            onHeightChange(v);
            saveToStorage("gen_height", v);
            persistGen({ height: v });
          }}
          style={{
            height: 22,
            background: "var(--theme-input-bg)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 4,
            color: "var(--theme-text)",
            fontSize: 10,
            textAlign: "center",
            padding: "0 2px",
            width: 56,
          }}
        />
      </div>
    </div>,
    document.body,
  );
}
