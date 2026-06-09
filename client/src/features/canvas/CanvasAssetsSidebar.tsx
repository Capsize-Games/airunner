import { useState, useCallback, useRef, useEffect } from "react";
import LucideIcon from "../../components/shared/LucideIcon";
import CanvasLayersSidebar from "./CanvasLayersSidebar";
import ImageBrowserPanel from "../../components/panels/ImageBrowserPanel";
import CollapsedRail from "./sidebar/CollapsedRail";
import ToolRow from "./sidebar/ToolRow";
import BrushControls from "./sidebar/BrushControls";
import type { AssetTab } from "./sidebar/CollapsedRail";

const LS_W         = "airunner_assets_sidebar_w";
const LS_TAB       = "airunner_assets_sidebar_tab";
const LS_COLLAPSED = "airunner_assets_sidebar_collapsed";

const TABS: { id: AssetTab; icon: string; label: string }[] = [
  { id: "layers", icon: "layers", label: "Layers" },
  { id: "images", icon: "images", label: "Images" },
];

const railBtnStyle: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  color: "rgba(255,255,255,0.25)", padding: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  borderRadius: 4, width: 24, height: 24, flexShrink: 0,
};

const tabBtnBase: React.CSSProperties = {
  flex: 1, padding: "5px 4px", background: "transparent", border: "none",
  fontSize: 11, cursor: "pointer", display: "flex", alignItems: "center",
  justifyContent: "center", gap: 4, transition: "color 0.15s, border-color 0.15s",
};

function loadWidth(): number {
  try {
    const v = localStorage.getItem(LS_W);
    if (v !== null) return Number(v);
    const old = localStorage.getItem("airunner_layers_sidebar_w");
    return old !== null ? Number(old) : 220;
  } catch { return 220; }
}

export default function CanvasAssetsSidebar() {
  const [tab, setTab] = useState<AssetTab>(() => {
    try { return (localStorage.getItem(LS_TAB) as AssetTab) ?? "layers"; }
    catch { return "layers"; }
  });
  const [width, setWidth] = useState(loadWidth);
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_COLLAPSED) === "true"; }
    catch { return false; }
  });

  const dragging = useRef(false);
  const startX = useRef(0);
  const startW = useRef(0);

  useEffect(() => { try { localStorage.setItem(LS_W, String(width)); } catch { /* */ } }, [width]);
  useEffect(() => { try { localStorage.setItem(LS_TAB, tab); } catch { /* */ } }, [tab]);
  useEffect(() => { try { localStorage.setItem(LS_COLLAPSED, String(collapsed)); } catch { /* */ } }, [collapsed]);

  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    startX.current = e.clientX;
    startW.current = width;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      setWidth(Math.max(180, Math.min(500, startW.current - (ev.clientX - startX.current))));
    };
    const onUp = () => {
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [width]);

  const expand = (toTab?: AssetTab) => {
    if (toTab) setTab(toTab);
    setCollapsed(false);
  };

  if (collapsed) {
    return <CollapsedRail activeTab={tab} onExpand={expand} />;
  }

  return (
    <div style={{ width, flexShrink: 0, display: "flex", flexDirection: "row", overflow: "hidden" }}>
      {/* Resize handle */}
      <div
        onMouseDown={handleResizeMouseDown}
        style={{ width: 4, cursor: "col-resize", flexShrink: 0, background: "transparent", transition: "background 0.15s" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "rgba(99,153,255,0.3)"; }}
        onMouseLeave={(e) => { if (!dragging.current) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
      />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#181824", overflow: "hidden", minWidth: 0 }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "flex-end",
          flexShrink: 0, borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "2px 4px",
        }}>
          <span style={{ flex: 1, fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.25)", letterSpacing: "0.06em", paddingLeft: 4 }}>
            ASSETS
          </span>
          <button type="button" onClick={() => setCollapsed(true)} title="Collapse panel" style={railBtnStyle}>
            <LucideIcon name="chevron-right" size={13} />
          </button>
        </div>

        <ToolRow />
        <BrushControls />

        {/* Tab bar */}
        <div style={{ display: "flex", flexShrink: 0, borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              style={{
                ...tabBtnBase,
                background: tab === t.id ? "var(--theme-panel-bg)" : "transparent",
                borderBottom: tab === t.id ? "2px solid var(--bs-primary)" : "2px solid transparent",
                color: tab === t.id ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
              }}
            >
              <LucideIcon name={t.icon} size={12} />
              {t.label}
            </button>
          ))}
        </div>

        <div style={{ flex: 1, overflow: "hidden", minHeight: 0, display: "flex", flexDirection: "column" }}>
          {tab === "layers" ? <CanvasLayersSidebar /> : <ImageBrowserPanel />}
        </div>
      </div>
    </div>
  );
}
