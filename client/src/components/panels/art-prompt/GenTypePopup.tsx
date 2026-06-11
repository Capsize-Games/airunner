import { createPortal } from "react-dom";

interface GenTypePopupProps {
  anchor: { left: number; bottom: number } | null;
  generationType: "txt2img" | "img2img";
  onSelect: (v: "txt2img" | "img2img") => void;
}

export default function GenTypePopup({
  anchor,
  generationType,
  onSelect,
}: GenTypePopupProps) {
  if (!anchor) return null;

  return createPortal(
    <div
      id="art-gen-type-popup"
      className="bg-theme-panel d-flex flex-column"
      style={{
        position: "fixed",
        left: anchor.left,
        bottom: anchor.bottom,
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 6,
        zIndex: 1300,
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
        minWidth: 180,
        padding: "8px 0",
        gap: 2,
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
          padding: "4px 10px 6px",
        }}
      >
        Generation Type
      </div>

      <button
        type="button"
        onClick={() => onSelect("txt2img")}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 1,
          width: "100%",
          padding: "6px 12px",
          border: "none",
          background:
            generationType === "txt2img"
              ? "rgba(var(--theme-primary-rgb), 0.10)"
              : "transparent",
          cursor: "pointer",
          textAlign: "left",
          color:
            generationType === "txt2img"
              ? "var(--bs-primary)"
              : "var(--theme-text)",
          fontSize: "0.78rem",
          borderLeft:
            generationType === "txt2img"
              ? "2px solid var(--bs-primary)"
              : "2px solid transparent",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background =
            "rgba(var(--theme-text-rgb), 0.08)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background =
            generationType === "txt2img"
              ? "rgba(var(--theme-primary-rgb), 0.10)"
              : "transparent";
        }}
      >
        <span>Text-to-image</span>
        <span
          style={{
            fontSize: "0.65rem",
            opacity: 0.55,
            fontWeight: 400,
          }}
        >
          Generate from a text description alone
        </span>
      </button>

      <button
        type="button"
        onClick={() => onSelect("img2img")}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 1,
          width: "100%",
          padding: "6px 12px",
          border: "none",
          background:
            generationType === "img2img"
              ? "rgba(var(--theme-primary-rgb), 0.10)"
              : "transparent",
          cursor: "pointer",
          textAlign: "left",
          color:
            generationType === "img2img"
              ? "var(--bs-primary)"
              : "var(--theme-text)",
          fontSize: "0.78rem",
          borderLeft:
            generationType === "img2img"
              ? "2px solid var(--bs-primary)"
              : "2px solid transparent",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background =
            "rgba(var(--theme-text-rgb), 0.08)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background =
            generationType === "img2img"
              ? "rgba(var(--theme-primary-rgb), 0.10)"
              : "transparent";
        }}
      >
        <span>Image-to-image</span>
        <span
          style={{
            fontSize: "0.65rem",
            opacity: 0.55,
            fontWeight: 400,
          }}
        >
          Transform an existing image with a text prompt
        </span>
      </button>
    </div>,
    document.body,
  );
}

