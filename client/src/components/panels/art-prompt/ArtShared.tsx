import React from "react";

// Inject CSS for number spinners and range slider handles — cannot be done via inline styles
const ART_PROMPT_CSS = `
  .art-no-spin::-webkit-inner-spin-button,
  .art-no-spin::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
  .art-no-spin { -moz-appearance: textfield; appearance: textfield; }
  .art-slider { -webkit-appearance: none; appearance: none; }
  .art-slider::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--bs-primary); cursor: pointer; margin-top: -3.5px;
  }
  .art-slider::-moz-range-thumb {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--bs-primary); cursor: pointer; border: none;
  }
`;

if (typeof document !== "undefined") {
  const id = "art-prompt-styles";
  if (!document.getElementById(id)) {
    const el = document.createElement("style");
    el.id = id;
    el.textContent = ART_PROMPT_CSS;
    document.head.appendChild(el);
  }
}

export type ArtPopup = "settings" | "promptSettings" | null;
export type ArtPanel = "lora" | "embeddings" | "savedPrompts" | null;

export interface ArtSettingsData {
  steps: number;
  cfgScale: number;
  nSamples: number;
  imagesPerBatch: number;
  onStepsChange: (v: number) => void;
  onCfgScaleChange: (v: number) => void;
  onNSamplesChange: (v: number) => void;
  onImagesPerBatchChange: (v: number) => void;
}

export const POPUP_STYLE: React.CSSProperties = {
  position: "absolute",
  bottom: "calc(100% + 4px)",
  background: "var(--theme-panel-bg)",
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: 6,
  zIndex: 1200,
  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
  maxHeight: 400,
  overflowY: "auto",
  minWidth: 260,
};

export function Divider() {
  return (
    <span
      style={{
        width: 1, height: 14,
        background: "rgba(255,255,255,0.12)",
        flexShrink: 0,
      }}
    />
  );
}

export function PromptDivider({ label }: { label: string }) {
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "3px 10px",
        borderTop: "1px solid rgba(255,255,255,0.08)",
        background: "rgba(var(--theme-text-rgb), 0.03)",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
          textTransform: "uppercase", color: "var(--theme-text-secondary)",
          opacity: 0.6,
        }}
      >
        {label}
      </span>
    </div>
  );
}

export function ToolbarIconBtn({
  title, onClick, disabled, active, badge, children,
}: {
  title: string;
  onClick?: () => void;
  disabled?: boolean;
  active?: boolean;
  badge?: number;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button" title={title} onClick={onClick} disabled={disabled}
      style={{
        position: "relative",
        display: "flex", alignItems: "center", justifyContent: "center",
        width: 26, height: 26, padding: 0,
        background: active ? "rgba(255,255,255,0.08)" : "transparent",
        border: "none",
        cursor: disabled ? "default" : "pointer",
        borderRadius: 4,
        color: active ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
        flexShrink: 0,
        opacity: disabled ? 0.35 : 1,
      }}
      onMouseEnter={(e) => {
        if (!disabled && !active) {
          (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)";
          (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.45)";
          (e.currentTarget as HTMLButtonElement).style.background = "transparent";
        }
      }}
    >
      {children}
      {badge !== undefined && (
        <span
          style={{
            position: "absolute", top: 1, right: 1,
            width: 8, height: 8, borderRadius: "50%",
            background: "var(--bs-primary)",
            fontSize: 0,
          }}
        />
      )}
    </button>
  );
}

export function CompactSlider({
  label, value, min, max, step, float, onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  float?: boolean;
  onChange: (v: number) => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "stretch" }}>
      <span style={{
        display: "flex", alignItems: "center", justifyContent: "flex-end",
        padding: "0 6px",
        fontSize: 9, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase",
        color: "var(--theme-text-secondary)",
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRight: "none",
        borderRadius: "4px 0 0 4px",
        flexShrink: 0,
        width: 52,
      }}>
        {label}
      </span>
      <div style={{
        flex: 1, display: "flex", alignItems: "center", padding: "0 6px",
        border: "1px solid rgba(255,255,255,0.12)",
        borderLeft: "none", borderRight: "none",
        minWidth: 0,
      }}>
        <input
          type="range"
          className="art-slider"
          min={min} max={max} step={step} value={value}
          onChange={(e) => onChange(float ? parseFloat(e.target.value) : parseInt(e.target.value, 10))}
          style={{ flex: 1, minWidth: 0, height: 3, accentColor: "var(--bs-primary)", cursor: "pointer" }}
        />
      </div>
      <span style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "0 6px",
        fontSize: 9, color: "var(--theme-text)",
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.12)",
        borderLeft: "none",
        borderRadius: "0 4px 4px 0",
        flexShrink: 0,
        width: 34,
      }}>
        {float ? value.toFixed(1) : value}
      </span>
    </div>
  );
}
