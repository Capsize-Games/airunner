import { createPortal } from "react-dom";
import type { ArtOptionsResponse } from "../../../api/client";

interface InfoDropdownPopupProps {
  field: string | null;
  anchor: { left: number; bottom: number; minWidth: number } | null;
  version: string;
  modelPath: string;
  scheduler: string;
  generationType: "txt2img" | "img2img";
  artOptions: ArtOptionsResponse | null;
  availableSchedulers: { label: string; value: string }[];
  onSelectVersion: (v: string) => void;
  onSelectModel: (m: string) => void;
  onSelectScheduler: (s: string) => void;
  onSelectGenType: (v: "txt2img" | "img2img") => void;
  onClose: () => void;
}

function genTypeBtn(
  type: "txt2img" | "img2img",
  current: "txt2img" | "img2img",
  onSelect: (v: "txt2img" | "img2img") => void,
  onClose: () => void,
) {
  const active = type === current;
  const label = type === "txt2img" ? "Text-to-image" : "Image-to-image";
  const desc = type === "txt2img"
    ? "Generate from a text description alone"
    : "Transform an existing image with a text prompt";
  return (
    <button type="button"
      onClick={() => { onSelect(type); onClose(); }}
      style={{
        display: "flex", flexDirection: "column", gap: 1,
        width: "100%", padding: "6px 12px", border: "none",
        background: active ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent",
        cursor: "pointer", textAlign: "left",
        color: active ? "var(--bs-primary)" : "var(--theme-text)",
        fontSize: "0.78rem",
        borderLeft: active ? "2px solid var(--bs-primary)" : "2px solid transparent",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(var(--theme-text-rgb), 0.08)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = active ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent"; }}
    >
      <span>{label}</span>
      <span style={{ fontSize: "0.65rem", opacity: 0.55, fontWeight: 400 }}>{desc}</span>
    </button>
  );
}

export default function InfoDropdownPopup({
  field, anchor, version, modelPath, scheduler, generationType,
  artOptions, availableSchedulers,
  onSelectVersion, onSelectModel, onSelectScheduler,
  onSelectGenType, onClose,
}: InfoDropdownPopupProps) {
  if (!field || !anchor) return null;

  return createPortal(
    <div id="art-info-dropdown-popup" className="bg-theme-panel overflow-y-auto"
      style={{
        position: "fixed", left: anchor.left, bottom: anchor.bottom,
        minWidth: Math.max(anchor.minWidth, 160), maxWidth: 280,
        border: "1px solid rgba(255,255,255,0.14)", borderRadius: 6,
        zIndex: 1300, boxShadow: "0 4px 20px rgba(0,0,0,0.5)", maxHeight: 240,
      }}
    >
      {field === "gentype" ? (
        <>
          {genTypeBtn("txt2img", generationType, onSelectGenType, onClose)}
          {genTypeBtn("img2img", generationType, onSelectGenType, onClose)}
        </>
      ) : (
        (() => {
          const options =
            field === "version"
              ? (artOptions?.versions?.map((v) => ({ label: v.name, value: v.name })) ?? [])
              : field === "model"
                ? (artOptions?.versions?.find((v) => v.name === version)?.models ?? [])
                : availableSchedulers;

          if (options.length === 0) {
            return <div style={{ padding: "8px 12px", fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}>No options</div>;
          }

          return options.map((opt: { label: string; value: string }) => {
            const currentValue = field === "version" ? version : field === "model" ? modelPath : scheduler;
            return (
              <button key={opt.value} type="button"
                onClick={() => {
                  if (field === "version") onSelectVersion(opt.value);
                  else if (field === "model") onSelectModel(opt.value);
                  else onSelectScheduler(opt.value);
                  onClose();
                }}
                style={{
                  display: "flex", alignItems: "center", width: "100%",
                  padding: "5px 12px",
                  background: opt.value === currentValue ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent",
                  border: "none",
                  borderLeft: opt.value === currentValue ? "2px solid var(--bs-primary)" : "2px solid transparent",
                  cursor: "pointer", textAlign: "left",
                  color: opt.value === currentValue ? "var(--bs-primary)" : "var(--theme-text)",
                  fontSize: "0.78rem",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background =
                    opt.value === currentValue ? "rgba(var(--theme-primary-rgb), 0.18)" : "rgba(var(--theme-text-rgb), 0.08)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background =
                    opt.value === currentValue ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent";
                }}
              >
                {opt.label}
              </button>
            );
          });
        })()
      )}
    </div>,
    document.body,
  );
}
