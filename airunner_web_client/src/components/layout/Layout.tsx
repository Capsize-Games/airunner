import {
  type ReactNode,
  useEffect,
  useState,
} from "react";
import { KnowledgeBasePanel } from "../panels/KnowledgeBasePanel";
import { ChatHistoryPanel } from "../panels/ChatHistoryPanel";
import { LLMSettingsPanel } from "../panels/LLMSettingsPanel";
import ArtModelPanel from "../panels/ArtModelPanel";
import ArtPromptPanel from "../panels/ArtPromptPanel";
import CanvasPanel from "../panels/CanvasPanel";
import LoraPanel from "../panels/LoraPanel";
import EmbeddingsPanel from "../panels/EmbeddingsPanel";
import LayersPanel from "../panels/LayersPanel";
import GridPanel from "../panels/GridPanel";
import ImageBrowserPanel from "../panels/ImageBrowserPanel";
import StatsPanel from "../panels/StatsPanel";

type PanelId =
  | "knowledge"
  | "history"
  | "llm_settings"
  | "art_model"
  | "lora"
  | "embeddings"
  | "layers"
  | "grid"
  | "image_browser"
  | "stats";

interface LayoutProps {
  children: ReactNode;
  leftPanel: PanelId | null;
  onLeftPanel: (id: PanelId) => void;
  rightPanel: PanelId | null;
  onRightPanel: (id: PanelId) => void;
  showChat: boolean;
  onToggleChat: () => void;
  showCanvas: boolean;
  onToggleCanvas: () => void;
  ttsOn: boolean;
  onToggleTts: () => void;
  sttOn: boolean;
  onToggleStt: () => void;
  onOpenSettings: () => void;
  onSelectConversation: (id: number) => void;
}

const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

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

/* ── Shared drag-ref used across mousedown → mousemove → mouseup ── */
let dragState: {
  key: string;
  setter: (v: number) => void;
  startX: number;
  startW: number;
  minW: number;
  maxW: number;
} | null = null;

function onGlobalMouseMove(e: MouseEvent) {
  const d = dragState;
  if (!d) return;
  const delta = e.clientX - d.startX;
  // Left-handle panels grow when dragging RIGHT (+delta).
  // The right-panel handle grows when dragging LEFT (-delta)
  // because the panel sits to the right of the handle.
  const sign = d.key === "right" ? -1 : 1;
  const next = Math.min(d.maxW, Math.max(d.minW, d.startW + sign * delta));
  d.setter(next);
}

function onGlobalMouseUp() {
  if (!dragState) return;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  dragState = null;
}

// Register once at module scope so the listeners aren't re-added
// every time the Layout component re-renders.
if (typeof window !== "undefined") {
  window.addEventListener("mousemove", onGlobalMouseMove);
  window.addEventListener("mouseup", onGlobalMouseUp);
}

export default function Layout({
  children,
  leftPanel,
  onLeftPanel,
  rightPanel,
  onRightPanel,
  showChat,
  onToggleChat,
  showCanvas,
  onToggleCanvas,
  ttsOn,
  onToggleTts,
  sttOn,
  onToggleStt,
  onOpenSettings,
  onSelectConversation,
}: LayoutProps) {
  const active = (id: PanelId, panel: PanelId | null) =>
    panel === id ? "active" : "";

  const [leftPanelW, setLeftPanelW] = useState(() =>
    loadNum("airunner_left_panel_w", 260),
  );
  const [chatW, setChatW] = useState(() =>
    loadNum("airunner_chat_w", 400),
  );
  const [rightPanelW, setRightPanelW] = useState(() =>
    loadNum("airunner_right_panel_w", 260),
  );

  useEffect(() => saveNum("airunner_left_panel_w", leftPanelW), [leftPanelW]);
  useEffect(() => saveNum("airunner_chat_w", chatW), [chatW]);
  useEffect(() => saveNum("airunner_right_panel_w", rightPanelW), [rightPanelW]);

  const makeHandle = (
    key: string,
    setter: (v: number) => void,
    minW: number,
    maxW: number,
    getW: () => number,
  ) => (
    <div
      className={`resize-handle ${dragState?.key === key ? "dragging" : ""}`}
      onMouseDown={(e: React.MouseEvent) => {
        e.preventDefault();
        dragState = { key, setter, startX: e.clientX, startW: getW(), minW, maxW };
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
      }}
    />
  );

  return (
    <div className="app-shell">
      {/* ── Top bar ── */}
      <div className="topbar">
        <div className="topbar-logo">
          <img src={icon("brain")} alt="" />
          AI <span>Runner</span>
        </div>
      </div>

      {/* ── Main row ── */}
      <div className="main-row">
        {/* ── Left icon bar ── */}
        <div className="icon-bar left">
          <button className={showChat ? "active" : ""} onClick={onToggleChat} title="Toggle Chat">
            <img src={icon("message-square-text")} alt="" />
          </button>
          <hr />
          <button className={active("knowledge", leftPanel)} onClick={() => onLeftPanel("knowledge")} title="Knowledge Base">
            <img src={icon("book")} alt="" />
          </button>
          <button className={active("history", leftPanel)} onClick={() => onLeftPanel("history")} title="History">
            <img src={icon("history")} alt="" />
          </button>
          <button className={active("llm_settings", leftPanel)} onClick={() => onLeftPanel("llm_settings")} title="LLM Settings">
            <img src={icon("settings-2")} alt="" />
          </button>
          <div className="flex-spacer" />
          <button className={ttsOn ? "active" : ""} onClick={onToggleTts} title="Text to Speech">
            <img src={icon("speaker")} alt="TTS" />
          </button>
          <button className={sttOn ? "active" : ""} onClick={onToggleStt} title="Speech to Text">
            <img src={icon("mic")} alt="STT" />
          </button>
        </div>

        {/* ── Left collapsible panel ── */}
        <div className={leftPanel ? "collapsible-panel left" : "panel-hidden"} style={{ width: leftPanelW }}>
          {leftPanel === "knowledge" && <KnowledgeBasePanel />}
          {leftPanel === "history" && <ChatHistoryPanel onSelectConversation={onSelectConversation} />}
          {leftPanel === "llm_settings" && <LLMSettingsPanel />}
        </div>
        {leftPanel && makeHandle("left", setLeftPanelW, 180, 500, () => leftPanelW)}

        {/* ── Chat panel ── */}
        {showChat && (
          <>
            <div className="chat-panel" style={{ width: chatW, flex: "none" }}>
              {children}
            </div>
            {makeHandle("chat", setChatW, 260, 800, () => chatW)}
          </>
        )}

        {/* ── Center area: canvas + art prompt fills remaining space ── */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {showCanvas && (
            <>
              <CanvasPanel />
              <div className="art-prompt-panel">
                <ArtPromptPanel />
              </div>
            </>
          )}
          {!showCanvas && <div style={{ flex: 1 }} />}
        </div>

        {/* ── Right group: handle | right-panel | right-icon-bar ── */}
        <div style={{ display: "flex", flexShrink: 0 }}>

          {rightPanel && makeHandle("right", setRightPanelW, 180, 500, () => rightPanelW)}
          <div className={rightPanel ? "collapsible-panel right" : "panel-hidden"} style={{ width: rightPanelW }}>
            {rightPanel === "art_model" && <ArtModelPanel />}
            {rightPanel === "lora" && <LoraPanel />}
            {rightPanel === "embeddings" && <EmbeddingsPanel />}
            {rightPanel === "layers" && <LayersPanel />}
            {rightPanel === "grid" && <GridPanel />}
            {rightPanel === "image_browser" && <ImageBrowserPanel />}
            {rightPanel === "stats" && <StatsPanel />}
          </div>

          {/* ── Right icon bar ── */}
        <div className="icon-bar right">
          <button className={showCanvas ? "active" : ""} onClick={onToggleCanvas} title="Canvas">
            <img src={icon("image")} alt="Canvas" />
          </button>
          <hr />
          <button className={active("art_model", rightPanel)} onClick={() => onRightPanel("art_model")} title="Art Model">
            <img src={icon("sparkles")} alt="Model" />
          </button>
          <button className={active("lora", rightPanel)} onClick={() => onRightPanel("lora")} title="LoRA">
            <img src={icon("puzzle")} alt="LoRA" />
          </button>
          <button className={active("embeddings", rightPanel)} onClick={() => onRightPanel("embeddings")} title="Embeddings">
            <img src={icon("scan-text")} alt="Embeddings" />
          </button>
          <button className={active("layers", rightPanel)} onClick={() => onRightPanel("layers")} title="Layers">
            <img src={icon("layers")} alt="Layers" />
          </button>
          <button className={active("grid", rightPanel)} onClick={() => onRightPanel("grid")} title="Grid">
            <img src={icon("grid-2x2-check")} alt="Grid" />
          </button>
          <button className={active("image_browser", rightPanel)} onClick={() => onRightPanel("image_browser")} title="Image Browser">
            <img src={icon("images")} alt="Browser" />
          </button>
          <button className={active("stats", rightPanel)} onClick={() => onRightPanel("stats")} title="Stats">
            <img src={icon("activity")} alt="Stats" />
          </button>
          <div className="flex-spacer" />
          <button onClick={onOpenSettings} title="Settings">
            <img src={icon("settings")} alt="Settings" />
          </button>
        </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="footer-bar">
        © {new Date().getFullYear()} Capsize LLC — All rights reserved.
      </div>
    </div>
  );
}
