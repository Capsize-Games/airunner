import { useState, useRef, useEffect } from "react";
import LucideIcon from "../../shared/LucideIcon";
import { ToolbarIconBtn, POPUP_STYLE, type ArtPopup, type ArtSettingsData } from "./ArtShared";
import { SettingsPopup } from "./SettingsPopup";

const NUM_INPUT_STYLE: React.CSSProperties = {
  height: 24, background: "var(--theme-input-bg)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 4, color: "var(--theme-text)",
  fontSize: 10, textAlign: "center", padding: "0 2px",
};

const NUM_INPUT_STYLE_SM: React.CSSProperties = {
  height: 22, background: "var(--theme-input-bg)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 4, color: "var(--theme-text)",
  fontSize: 10, textAlign: "center", padding: "0 2px", width: 56,
};

interface Props {
  seed: number;
  seedRandomized: boolean;
  genWidth: number;
  genHeight: number;
  openPopup: ArtPopup;
  settings: ArtSettingsData;
  onSeedChange: (v: number) => void;
  onToggleRandom: () => void;
  onWidthChange: (v: number) => void;
  onHeightChange: (v: number) => void;
  onTogglePopup: (popup: NonNullable<ArtPopup>) => void;
}

export function PromptToolbar({
  seed, seedRandomized, genWidth, genHeight, openPopup, settings,
  onSeedChange, onToggleRandom, onWidthChange, onHeightChange, onTogglePopup,
}: Props) {
  const [showSize, setShowSize] = useState(false);
  const sizeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showSize) return;
    const handler = (e: MouseEvent) => {
      if (sizeRef.current && !sizeRef.current.contains(e.target as Node))
        setShowSize(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showSize]);

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 4,
      padding: "4px 6px",
      borderTop: "1px solid rgba(255,255,255,0.08)",
      flexShrink: 0,
    }}>
      {/* Settings button */}
      <div style={{ position: "relative" }}>
        <ToolbarIconBtn
          title="Generation settings"
          onClick={() => onTogglePopup("settings")}
          active={openPopup === "settings"}
        >
          <LucideIcon name="settings-2" size={14} />
        </ToolbarIconBtn>
        {openPopup === "settings" && (
          <div style={{ ...POPUP_STYLE, left: 0 }}>
            <SettingsPopup {...settings} />
          </div>
        )}
      </div>

      {/* Seed affixed group */}
      <div style={{ display: "flex", alignItems: "stretch" }}>
        <span style={{
          display: "flex", alignItems: "center", padding: "0 5px",
          fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
          textTransform: "uppercase", color: "var(--theme-text-secondary)",
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRight: "none", borderRadius: "4px 0 0 4px",
          flexShrink: 0,
        }}>
          Seed
        </span>
        <input
          type="number" className="art-no-spin"
          value={seed} readOnly={seedRandomized}
          onChange={(e) => { const v = Number(e.target.value); if (!isNaN(v)) onSeedChange(v); }}
          style={{
            ...NUM_INPUT_STYLE, width: "calc(10ch + 10px)",
            borderRadius: 0, borderRight: "none",
            color: seedRandomized ? "rgba(255,255,255,0.3)" : "var(--theme-text)",
          }}
        />
        <button
          type="button"
          title={seedRandomized ? "Use fixed seed" : "Randomize seed"}
          onClick={onToggleRandom}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            width: 24, padding: 0, flexShrink: 0,
            background: seedRandomized ? "var(--bs-primary)" : "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderLeft: "none", borderRadius: "0 4px 4px 0",
            cursor: "pointer",
            color: seedRandomized ? "#fff" : "rgba(255,255,255,0.45)",
          }}
        >
          <LucideIcon name="dices" size={13} />
        </button>
      </div>

      {/* Size picker */}
      <div ref={sizeRef} style={{ position: "relative" }}>
        <button
          type="button"
          onClick={() => setShowSize((v) => !v)}
          style={{
            background: showSize ? "rgba(255,255,255,0.08)" : "transparent",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 4,
            color: "rgba(255,255,255,0.55)",
            fontSize: 9, fontWeight: 700, letterSpacing: "0.05em",
            padding: "0 6px", height: 24, cursor: "pointer", flexShrink: 0,
            whiteSpace: "nowrap",
          }}
        >
          {genWidth}×{genHeight}
        </button>
        {showSize && (
          <div style={{
            position: "absolute", bottom: "calc(100% + 4px)", left: 0,
            background: "var(--theme-panel-bg)",
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 6,
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            padding: "10px 12px",
            display: "flex", flexDirection: "column", gap: 8,
            zIndex: 1200,
          }}>
            <div style={{
              fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
              textTransform: "uppercase", color: "var(--theme-text-secondary)",
              opacity: 0.6, marginBottom: 6,
            }}>Image Size</div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>W</span>
              <input
                type="number" className="art-no-spin"
                min={64} max={2048} step={64} value={genWidth}
                onChange={(e) => onWidthChange(Math.max(64, Math.min(2048, Number(e.target.value))))}
                style={NUM_INPUT_STYLE_SM}
              />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>H</span>
              <input
                type="number" className="art-no-spin"
                min={64} max={2048} step={64} value={genHeight}
                onChange={(e) => onHeightChange(Math.max(64, Math.min(2048, Number(e.target.value))))}
                style={NUM_INPUT_STYLE_SM}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
