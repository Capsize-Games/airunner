import { useState, useCallback, useRef, useEffect } from "react";
import LucideIcon from "../../components/shared/LucideIcon";
import CanvasLayersSidebar from "./CanvasLayersSidebar";
import ImageBrowserPanel from "../../components/panels/ImageBrowserPanel";
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

export default function CanvasAssetsSidebar({
  visible = true,
  activeTab,
}: {
  visible?: boolean;
  activeTab?: AssetTab;
}) {
  if (!visible) return null;

  const [tab, setTab] = useState<AssetTab>(() => {
    try { return (localStorage.getItem(LS_TAB) as AssetTab) ?? "layers"; }
    catch { return "layers"; }
  });

  useEffect(() => {
    if (activeTab) setTab(activeTab);
  }, [activeTab]);
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
      setWidth(Math.max(260, Math.min(500, startW.current - (ev.clientX - startX.current))));
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

  return (
    <div className="flex-shrink-0 d-flex overflow-hidden" style={{ width }}>
      {/* Resize handle */}
      <div
        onMouseDown={handleResizeMouseDown}
        className="flex-shrink-0"
        style={{ width: 4, cursor: "col-resize", background: "transparent", transition: "background 0.15s" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = "rgba(99,153,255,0.3)"; }}
        onMouseLeave={(e) => { if (!dragging.current) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
      />

      <div className="flex-grow-1 d-flex flex-column overflow-hidden" style={{ background: "#14141e", minWidth: 0 }}>

        {/* Tab bar */}
        <div className="d-flex flex-shrink-0 border-b-subtle" style={{ background: "#161620" }}>
          {TABS.map((t) => {
            const isActive = tab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                style={{
                  ...tabBtnBase,
                  background: isActive ? "var(--theme-panel-bg)" : "transparent",
                  borderBottom: isActive ? "2px solid var(--bs-primary)" : "2px solid transparent",
                  color: isActive ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
                }}
                onMouseEnter={(e) => {
                  if (!isActive)
                    e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                }}
                onMouseLeave={(e) => {
                  if (!isActive)
                    e.currentTarget.style.background = "transparent";
                }}
              >
                <LucideIcon name={t.icon} size={12} />
                {t.label}
              </button>
            );
          })}
        </div>

        <div className="flex-grow-1 overflow-hidden d-flex flex-column min-h-0">
          {tab === "layers" ? <CanvasLayersSidebar /> : <ImageBrowserPanel />}
        </div>
      </div>
    </div>
  );
}
