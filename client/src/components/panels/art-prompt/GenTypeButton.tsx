import type { RefObject } from "react";
import LucideIcon from "../../shared/LucideIcon";
import GenTypePopup from "./GenTypePopup";

interface GenTypeButtonProps {
  genTypeBtnRef: RefObject<HTMLDivElement | null>;
  showGenType: boolean;
  toggleGenType: () => void;
  genTypeAnchor: { left: number; bottom: number } | null;
  generationType: "txt2img" | "img2img";
  onSetGenerationType: (v: "txt2img" | "img2img") => void;
  closeGenType: () => void;
}

export default function GenTypeButton({
  genTypeBtnRef,
  showGenType,
  toggleGenType,
  genTypeAnchor,
  generationType,
  onSetGenerationType,
  closeGenType,
}: GenTypeButtonProps) {
  return (
    <>
      <div ref={genTypeBtnRef}>
        <button
          type="button"
          title="Generation type"
          onClick={toggleGenType}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: 26,
            padding: "0 6px",
            background: showGenType
              ? "rgba(255,255,255,0.08)"
              : "transparent",
            border: "none",
            cursor: "pointer",
            borderRadius: 4,
            color: showGenType
              ? "var(--bs-primary)"
              : "rgba(255,255,255,0.45)",
            flexShrink: 0,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.03em",
            fontVariant: "small-caps",
            whiteSpace: "nowrap",
          }}
          onMouseEnter={(e) => {
            if (!showGenType) {
              e.currentTarget.style.color =
                "rgba(255,255,255,0.85)";
              e.currentTarget.style.background =
                "rgba(255,255,255,0.08)";
            }
          }}
          onMouseLeave={(e) => {
            if (!showGenType) {
              e.currentTarget.style.color =
                "rgba(255,255,255,0.45)";
              e.currentTarget.style.background = "transparent";
            }
          }}
        >
          <LucideIcon name="image-plus" size={13} />
        </button>
      </div>
      <GenTypePopup
        anchor={showGenType ? genTypeAnchor : null}
        generationType={generationType}
        onSelect={(v) => {
          onSetGenerationType(v);
          closeGenType();
        }}
      />
    </>
  );
}
