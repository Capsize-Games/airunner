import type { RefObject } from "react";
import LucideIcon from "../../shared/LucideIcon";
import SizePopup from "./SizePopup";

interface SizeButtonProps {
  sizeBtnRef: RefObject<HTMLDivElement | null>;
  showSize: boolean;
  toggleSize: () => void;
  sizeAnchor: { left: number; bottom: number } | null;
  sizePortalId: string;
  genWidth: number;
  genHeight: number;
  onWidthChange: (v: number) => void;
  onHeightChange: (v: number) => void;
  persistGen: (updates: Record<string, unknown>) => void;
}

export default function SizeButton({
  sizeBtnRef,
  showSize,
  toggleSize,
  sizeAnchor,
  sizePortalId,
  genWidth,
  genHeight,
  onWidthChange,
  onHeightChange,
  persistGen,
}: SizeButtonProps) {
  return (
    <>
      <div ref={sizeBtnRef}>
        <button
          type="button"
          title="Image size"
          onClick={toggleSize}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 26,
            padding: "0 6px",
            background: showSize
              ? "rgba(255,255,255,0.08)"
              : "transparent",
            border: "none",
            cursor: "pointer",
            borderRadius: 4,
            color: showSize
              ? "var(--bs-primary)"
              : "rgba(255,255,255,0.45)",
            flexShrink: 0,
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.03em",
          }}
          onMouseEnter={(e) => {
            if (!showSize) {
              e.currentTarget.style.color =
                "rgba(255,255,255,0.85)";
              e.currentTarget.style.background =
                "rgba(255,255,255,0.08)";
            }
          }}
          onMouseLeave={(e) => {
            if (!showSize) {
              e.currentTarget.style.color =
                "rgba(255,255,255,0.45)";
              e.currentTarget.style.background = "transparent";
            }
          }}
        >
          <LucideIcon name="ruler-dimension-line" size={13} />
        </button>
      </div>
      <SizePopup
        anchor={showSize ? sizeAnchor : null}
        portalId={sizePortalId}
        genWidth={genWidth}
        genHeight={genHeight}
        onWidthChange={onWidthChange}
        onHeightChange={onHeightChange}
        persistGen={persistGen}
      />
    </>
  );
}
