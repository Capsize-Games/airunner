import {
  type ReactNode,
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
} from "react";
import CanvasPanel from "../panels/CanvasPanel";
import CivitaiBrowserPanel from "../panels/civitai-browser/CivitaiBrowserPanel";
import DownloadTray from "../downloads/DownloadTray";
import TopBar from "./TopBar";
import { isWsConnected } from "../../features/api/WsApiClient";
import { LeftIconBar } from "./IconBar";
import { CanvasProvider } from "../../features/canvas";
import type { HardwareProfile } from "../../types/api";
import LucideIcon from "../shared/LucideIcon";

const StatsPanel = lazy(() => import("../panels/StatsPanel"));

const HANDLE_W = 4;
const CHAT_MIN = 260;
const CANVAS_MIN = 400;

type PanelId = "civitai_browser";

interface LayoutProps {
  children: ReactNode;
  rightPanel: PanelId | null;
  onRightPanel: (id: PanelId) => void;
  showChat: boolean;
  onToggleChat: () => void;
  showCanvas: boolean;
  onToggleCanvas: () => void;
  onOpenSettings: () => void;
  onSelectConversation: (id: number) => void;
  bottomBarSlot?: React.ReactNode;
}

function saveNum(key: string, val: number) {
  try { localStorage.setItem(key, String(val)); } catch { /* */ }
}

function loadNum(key: string, fallback: number): number {
  try {
    const v = localStorage.getItem(key);
    return v !== null ? Number(v) : fallback;
  } catch {
    return fallback;
  }
}

/* ── Drag state (module-level, captured at mousedown) ── */
let dragState: {
  startX: number;
  startChatW: number;
  maxChatW: number;
  setChatW: (w: number) => void;
} | null = null;

function onGlobalMouseMove(e: MouseEvent) {
  if (!dragState) return;
  const delta = e.clientX - dragState.startX;
  dragState.setChatW(
    Math.max(CHAT_MIN, Math.min(dragState.maxChatW, dragState.startChatW + delta)),
  );
}

function onGlobalMouseUp() {
  if (!dragState) return;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  dragState = null;
}

if (typeof window !== "undefined") {
  window.addEventListener("mousemove", onGlobalMouseMove);
  window.addEventListener("mouseup", onGlobalMouseUp);
}

export default function Layout({
  children,
  rightPanel,
  onRightPanel,
  showChat,
  onToggleChat,
  showCanvas,
  onToggleCanvas,
  onOpenSettings,
  onSelectConversation: _onSelectConversation,
  bottomBarSlot,
}: LayoutProps) {
  const panelsRef = useRef<HTMLDivElement>(null);
  const [panelsWidth, setPanelsWidth] = useState(0);

  useEffect(() => {
    const el = panelsRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) setPanelsWidth(entry.contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const [chatW, setChatW] = useState(() => loadNum("airunner_chat_w", 400));

  // Clamp chat width when container or visibility changes.
  useEffect(() => {
    if (panelsWidth === 0 || !showChat) return;
    const max = panelsWidth - (showCanvas ? CANVAS_MIN + HANDLE_W : 0);
    if (chatW > max) setChatW(Math.max(CHAT_MIN, max));
  }, [panelsWidth, showChat, showCanvas]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => saveNum("airunner_chat_w", chatW), [chatW]);

  const makeHandle = () => {
    const onDown = (e: React.MouseEvent) => {
      e.preventDefault();
      dragState = {
        startX: e.clientX,
        startChatW: chatW,
        maxChatW: panelsWidth - CANVAS_MIN - HANDLE_W,
        setChatW,
      };
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    };
    return <div className="resize-handle" onMouseDown={onDown} />;
  };

  return (
    <div className="app-shell">
      <TopBar />

      <div className="main-row">
        <LeftIconBar
          showChat={showChat}
          showCanvas={showCanvas}
          rightPanel={rightPanel}
          onToggleChat={onToggleChat}
          onToggleCanvas={onToggleCanvas}
          onRightPanel={onRightPanel}
          onOpenSettings={onOpenSettings}
          bottomSlot={bottomBarSlot}
        />

        {/* ── Panels container ── */}
        <div
          ref={panelsRef}
          style={{ flex: 1, display: "flex", overflow: "hidden", minWidth: 0 }}
        >
          {/* Chat */}
          {showChat && (
            <div
              className="chat-panel"
              style={
                showCanvas
                  ? { width: chatW, flex: "none", overflow: "hidden" }
                  : { flex: 1, minWidth: 0, overflow: "hidden" }
              }
            >
              {children}
            </div>
          )}

          {showChat && showCanvas && makeHandle()}

          {/* Main content — canvas or CivitAI browser (full-width mode) */}
          {showCanvas && (
            <div style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
              {rightPanel === "civitai_browser" ? (
                <CivitaiBrowserPanel />
              ) : (
                <CanvasProvider>
                  <CanvasPanel />
                </CanvasProvider>
              )}
            </div>
          )}

          {/* Welcome screen — shown when no panels are open */}
          {!showChat && !showCanvas && (
            <WelcomeScreen
              onOpenChat={onToggleChat}
              onOpenCanvas={onToggleCanvas}
              onOpenCivitai={() => onRightPanel("civitai_browser")}
            />
          )}
        </div>

      </div>

      <DownloadTray />

      <div
        className="footer-bar"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0 12px",
        }}
      >
        <span>
          &copy; {new Date().getFullYear()} Capsize LLC &mdash; All rights
          reserved.
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <FooterStats />
          <LiveIndicator />
        </div>
      </div>
    </div>
  );
}

function WelcomeScreen({
  onOpenChat,
  onOpenCanvas,
  onOpenCivitai,
}: {
  onOpenChat: () => void;
  onOpenCanvas: () => void;
  onOpenCivitai: () => void;
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  const items = [
    { key: "chat",   icon: "bot-message-square", label: "Chat",    hint: "Talk to a local LLM",          onClick: onOpenChat },
    { key: "canvas", icon: "image",              label: "Canvas",  hint: "Generate and edit images",      onClick: onOpenCanvas },
    { key: "civitai",icon: "globe",              label: "CivitAI", hint: "Browse and download models",    onClick: onOpenCivitai },
  ];

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        color: "var(--theme-text-secondary)",
        userSelect: "none",
        padding: "40px 24px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
        <img
          src="/favicon.svg"
          alt="AI Runner"
          style={{ width: 64, height: 64, opacity: 0.25, filter: "grayscale(1)" }}
        />
        <h2
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: "var(--theme-heading)",
            margin: 0,
            opacity: 0.6,
          }}
        >
          AI Runner
        </h2>
        <p style={{ margin: 0, fontSize: 13, opacity: 0.5, textAlign: "center", maxWidth: 320 }}>
          Open a panel from the sidebar to get started.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 340 }}>
        {items.map(({ key, icon, label, hint, onClick }) => (
          <button
            key={key}
            type="button"
            onClick={onClick}
            onMouseEnter={() => setHovered(key)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              padding: "11px 16px",
              borderRadius: 8,
              background: hovered === key
                ? "rgba(var(--theme-primary-rgb), 0.10)"
                : "rgba(var(--theme-text-rgb), 0.03)",
              border: hovered === key
                ? "1px solid rgba(var(--theme-primary-rgb), 0.30)"
                : "1px solid rgba(var(--theme-text-rgb), 0.07)",
              cursor: "pointer",
              textAlign: "left",
              width: "100%",
              transition: "background 0.15s, border-color 0.15s",
            }}
          >
            <span
              style={{
                flexShrink: 0,
                color: hovered === key ? "var(--bs-primary)" : "var(--theme-text-secondary)",
                transition: "color 0.15s",
              }}
            >
              <LucideIcon name={icon} size={20} />
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--theme-text)" }}>
                {label}
              </span>
              <span style={{ fontSize: 11, color: "var(--theme-text-secondary)", opacity: 0.7 }}>
                {hint}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function FooterStats() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    let canceled = false;
    const poll = async () => {
      try {
        const { getHardwareProfile } = await import("../../api/client");
        const data = await getHardwareProfile();
        if (!canceled) setHw(data);
      } catch { /* server may be unavailable */ }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => { canceled = true; clearInterval(id); };
  }, []);

  if (!hw || hw.total_vram_gb === 0) return null;

  const vramUsed = hw.total_vram_gb - hw.available_vram_gb;
  const vramPct = (vramUsed / hw.total_vram_gb) * 100;
  const ramUsed = hw.total_ram_gb - hw.available_ram_gb;
  const ramPct = (ramUsed / hw.total_ram_gb) * 100;

  const color = (pct: number) =>
    pct > 90 ? "#dc3545" : pct > 70 ? "#ffc107" : "rgba(255,255,255,0.4)";

  return (
    <span style={{ position: "relative", display: "flex", alignItems: "center" }}>
      <button
        onClick={() => setShowDetail((v) => !v)}
        title="Resource monitor"
        style={{
          background: "none", border: "none", cursor: "pointer", padding: 0,
          display: "flex", alignItems: "center", gap: 6,
          fontFamily: "monospace", fontSize: 11,
        }}
      >
        <span style={{ color: color(vramPct) }}>
          VRAM {vramUsed.toFixed(1)}/{hw.total_vram_gb.toFixed(0)}GB
        </span>
        <span style={{ color: "rgba(255,255,255,0.2)" }}>·</span>
        <span style={{ color: color(ramPct) }}>
          RAM {ramUsed.toFixed(1)}/{hw.total_ram_gb.toFixed(0)}GB
        </span>
      </button>
      {showDetail && (
        <div
          style={{
            position: "absolute", bottom: "calc(100% + 8px)", right: 0,
            zIndex: 9999,
          }}
        >
          <Suspense fallback={null}>
            <StatsPanel />
          </Suspense>
        </div>
      )}
    </span>
  );
}

function LiveIndicator() {
  const [connected, setConnected] = useState(isWsConnected);
  useEffect(() => {
    let canceled = false;
    const id = setInterval(() => {
      if (!canceled) setConnected(isWsConnected());
    }, 1000);
    return () => { canceled = true; clearInterval(id); };
  }, []);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11,
        fontFamily: "monospace",
        color: connected ? "rgba(0,200,100,0.7)" : "rgba(255,150,50,0.6)",
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: connected ? "rgb(0,200,100)" : "rgb(255,150,50)",
          display: "inline-block",
        }}
      />
      {connected ? "Live" : "Reconnecting…"}
    </span>
  );
}
