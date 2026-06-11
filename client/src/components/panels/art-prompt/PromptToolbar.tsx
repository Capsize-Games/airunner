import { useState, useRef, useEffect, useId } from "react";
import { createPortal } from "react-dom";
import LucideIcon from "../../shared/LucideIcon";

const NUM_INPUT_STYLE_SM: React.CSSProperties = {
  height: 22, background: "var(--theme-input-bg)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: 4, color: "var(--theme-text)",
  fontSize: 10, textAlign: "center", padding: "0 2px", width: 56,
};

interface Props {
  genWidth: number;
  genHeight: number;
  onWidthChange: (v: number) => void;
  onHeightChange: (v: number) => void;
}

export function PromptToolbar({
  genWidth, genHeight,
  onWidthChange, onHeightChange,
}: Props) {
  const [showSize, setShowSize] = useState(false);
  const sizeContainerRef = useRef<HTMLDivElement>(null);
  const sizeBtnRef = useRef<HTMLButtonElement>(null);
  const [sizeAnchor, setSizeAnchor] = useState<{ left: number; bottom: number } | null>(null);
  const emittingRef = useRef(false);

  useEffect(() => {
    if (!showSize) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const portalEl = document.getElementById(portalId);
      if (portalEl?.contains(target)) return;
      if (sizeContainerRef.current && !sizeContainerRef.current.contains(target))
        setShowSize(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showSize]);

  const portalId = useId();

  // Close when other overlays open
  useEffect(() => {
    const handler = () => {
      if (emittingRef.current) return;
      setShowSize(false);
    };
    window.addEventListener("art-overlay-opened", handler);
    window.addEventListener("chat-picker-opened", handler);
    return () => {
      window.removeEventListener("art-overlay-opened", handler);
      window.removeEventListener("chat-picker-opened", handler);
    };
  }, []);

  const handleSizeToggle = () => {
    const next = !showSize;
    setShowSize(next);
    if (next) {
      emittingRef.current = true;
      window.dispatchEvent(new Event("art-overlay-opened"));
      emittingRef.current = false;
      if (sizeBtnRef.current) {
        const r = sizeBtnRef.current.getBoundingClientRect();
        setSizeAnchor({ left: r.left, bottom: window.innerHeight - r.top + 4 });
      }
    }
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 4,
      padding: "4px 6px",
      borderTop: "1px solid rgba(255,255,255,0.08)",
      flexShrink: 0,
    }}>
      {/* Size picker */}
      <div ref={sizeContainerRef} className="position-relative">
        <button
          ref={sizeBtnRef}
          type="button"
          onClick={handleSizeToggle}
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
        {showSize && sizeAnchor && createPortal(
          <div id={portalId} className="d-flex flex-column bg-theme-panel" style={{
            position: "fixed", left: sizeAnchor.left, bottom: sizeAnchor.bottom,
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 6,
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            padding: "10px 12px",
            gap: 8,
            zIndex: 1300,
          }}>
            <div style={{
              fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
              textTransform: "uppercase", color: "var(--theme-text-secondary)",
              opacity: 0.6, marginBottom: 6,
            }}>Image Size</div>
            <div className="d-flex align-items-center" style={{ gap: 6 }}>
              <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>W</span>
              <input
                type="number" className="art-no-spin"
                value={genWidth}
                onChange={(e) => onWidthChange(Number(e.target.value))}
                onBlur={(e) => onWidthChange(Math.max(64, Math.min(2048, Number(e.target.value))))}
                style={NUM_INPUT_STYLE_SM}
              />
            </div>
            <div className="d-flex align-items-center" style={{ gap: 6 }}>
              <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>H</span>
              <input
                type="number" className="art-no-spin"
                value={genHeight}
                onChange={(e) => onHeightChange(Number(e.target.value))}
                onBlur={(e) => onHeightChange(Math.max(64, Math.min(2048, Number(e.target.value))))}
                style={NUM_INPUT_STYLE_SM}
              />
            </div>
          </div>,
          document.body
        )}
      </div>
    </div>
  );
}
