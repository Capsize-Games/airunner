import {
  type ReactNode,
  useEffect,
  useState,
  useRef,
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

const HANDLE_W = 4;
const LEFT_MIN = 180;
const CHAT_MIN = 260;
const CANVAS_MIN = 400;
const RIGHT_MIN = 180;

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

/* ── Drag state (module-level, captured at mousedown) ── */
let dragState: {
  key: string;
  startX: number;
  wL: number;
  wC: number;
  wV: number;
  wR: number;
  showChat: boolean;
  showCanvas: boolean;
  showRight: boolean;
  setL: (w: number) => void;
  setC: (w: number) => void;
  setV: (w: number) => void;
  setR: (w: number) => void;
} | null = null;

function onGlobalMouseMove(e: MouseEvent) {
  const d = dragState;
  if (!d) return;
  const delta = e.clientX - d.startX;

  if (d.key === "left-chat") {
    let room = 0;
    if (d.showCanvas) room += d.wV - CANVAS_MIN;
    if (d.showRight) room += d.wR - RIGHT_MIN;
    const clamped = Math.max(-(d.wL - LEFT_MIN), Math.min(room, delta));

    let remaining = clamped;
    let newV = d.wV;
    let newR = d.wR;
    if (d.showCanvas) {
      const s = Math.min(d.wV - CANVAS_MIN, remaining);
      newV = d.wV - s;
      remaining -= s;
    }
    if (d.showRight) {
      const s = Math.min(d.wR - RIGHT_MIN, remaining);
      newR = d.wR - s;
    }
    d.setL(d.wL + clamped);
    d.setV(newV);
    d.setR(newR);
  } else if (d.key === "left-canvas") {
    let room = 0;
    if (d.showCanvas) room += d.wV - CANVAS_MIN;
    if (d.showRight) room += d.wR - RIGHT_MIN;
    const clamped = Math.max(-(d.wL - LEFT_MIN), Math.min(room, delta));

    let remaining = clamped;
    let newV = d.wV;
    let newR = d.wR;
    if (d.showCanvas) {
      const s = Math.min(d.wV - CANVAS_MIN, remaining);
      newV = d.wV - s;
      remaining -= s;
    }
    if (d.showRight) {
      const s = Math.min(d.wR - RIGHT_MIN, remaining);
      newR = d.wR - s;
    }
    d.setL(d.wL + clamped);
    d.setV(newV);
    d.setR(newR);
  } else if (d.key === "left-right") {
    const room = d.wR - RIGHT_MIN;
    const clamped = Math.max(-(d.wL - LEFT_MIN), Math.min(room, delta));
    d.setL(d.wL + clamped);
    d.setR(d.wR - clamped);
  } else if (d.key === "chat-canvas") {
    let room = 0;
    if (d.showCanvas) room += d.wV - CANVAS_MIN;
    if (d.showRight) room += d.wR - RIGHT_MIN;
    const clamped = Math.max(-(d.wC - CHAT_MIN), Math.min(room, delta));

    let remaining = clamped;
    let newV = d.wV;
    let newR = d.wR;
    if (d.showCanvas) {
      const s = Math.min(d.wV - CANVAS_MIN, remaining);
      newV = d.wV - s;
      remaining -= s;
    }
    if (d.showRight) {
      const s = Math.min(d.wR - RIGHT_MIN, remaining);
      newR = d.wR - s;
    }
    d.setC(d.wC + clamped);
    d.setV(newV);
    d.setR(newR);
  } else if (d.key === "chat-right") {
    const room = d.wR - RIGHT_MIN;
    const clamped = Math.max(-(d.wC - CHAT_MIN), Math.min(room, delta));
    d.setC(d.wC + clamped);
    d.setR(d.wR - clamped);
  } else if (d.key === "canvas-right") {
    const room = d.wR - RIGHT_MIN;
    const clamped = Math.max(-(d.wV - CANVAS_MIN), Math.min(room, delta));
    d.setV(d.wV + clamped);
    d.setR(d.wR - clamped);
  }
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

  const panelsRef = useRef<HTMLDivElement>(null);
  const [panelsWidth, setPanelsWidth] = useState(0);

  useEffect(() => {
    const el = panelsRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setPanelsWidth(entry.contentRect.width);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const [leftPanelW, setLeftPanelW] = useState(() =>
    loadNum("airunner_left_panel_w", 260),
  );
  const [chatW, setChatW] = useState(() =>
    loadNum("airunner_chat_w", 400),
  );
  const [canvasW, setCanvasW] = useState(() =>
    loadNum("airunner_canvas_w", 600),
  );
  const [rightPanelW, setRightPanelW] = useState(() =>
    loadNum("airunner_right_panel_w", 260),
  );

  // Build ordered list of visible panels and their handles.
  const visible: string[] = [];
  if (leftPanel) visible.push("left");
  if (showChat) visible.push("chat");
  if (showCanvas) visible.push("canvas");
  if (rightPanel) visible.push("right");

  const numHandles = Math.max(0, visible.length - 1);
  // Fixed widths inside the panels container: only handles (icon bars
  // are siblings of the container, not inside it).
  const fixedWidths = numHandles * HANDLE_W;

  // Auto-clamp when panels container width or visibility changes.
  // Handles both overflow (shrink rightmost panels) and underflow
  // (expand the rightmost visible panel to fill empty space).
  useEffect(() => {
    if (panelsWidth === 0) return;
    const total =
      fixedWidths +
      (leftPanel ? leftPanelW : 0) +
      (showChat ? chatW : 0) +
      (showCanvas ? canvasW : 0) +
      (rightPanel ? rightPanelW : 0);

    if (total > panelsWidth) {
      let excess = total - panelsWidth;
      if (rightPanel) {
        const s = Math.min(rightPanelW - RIGHT_MIN, excess);
        setRightPanelW((w) => w - s);
        excess -= s;
      }
      if (showCanvas) {
        const s = Math.min(canvasW - CANVAS_MIN, excess);
        setCanvasW((w) => w - s);
        excess -= s;
      }
      if (showChat) {
        const s = Math.min(chatW - CHAT_MIN, excess);
        setChatW((w) => w - s);
        excess -= s;
      }
      if (leftPanel && excess > 0) {
        const s = Math.min(leftPanelW - LEFT_MIN, excess);
        setLeftPanelW((w) => w - s);
      }
    } else if (total < panelsWidth) {
      const slack = panelsWidth - total;
      if (rightPanel) {
        setRightPanelW((w) => w + slack);
      } else if (showCanvas) {
        setCanvasW((w) => w + slack);
      } else if (showChat) {
        setChatW((w) => w + slack);
      } else if (leftPanel) {
        setLeftPanelW((w) => w + slack);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [panelsWidth, leftPanel, showChat, showCanvas, rightPanel]);

  useEffect(() => saveNum("airunner_left_panel_w", leftPanelW), [leftPanelW]);
  useEffect(() => saveNum("airunner_chat_w", chatW), [chatW]);
  useEffect(() => saveNum("airunner_canvas_w", canvasW), [canvasW]);
  useEffect(() => saveNum("airunner_right_panel_w", rightPanelW), [rightPanelW]);

  const handlePairs: string[] = [];
  for (let i = 0; i < visible.length - 1; i++) {
    handlePairs.push(`${visible[i]}-${visible[i + 1]}`);
  }

  const makeHandle = (key: string) => {
    const onDown = (e: React.MouseEvent) => {
      e.preventDefault();
      dragState = {
        key,
        startX: e.clientX,
        wL: leftPanelW,
        wC: chatW,
        wV: canvasW,
        wR: rightPanelW,
        showChat,
        showCanvas,
        showRight: rightPanel !== null,
        setL: setLeftPanelW,
        setC: setChatW,
        setV: setCanvasW,
        setR: setRightPanelW,
      };
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    };
    return (
      <div
        className={`resize-handle ${dragState?.key === key ? "dragging" : ""}`}
        onMouseDown={onDown}
      />
    );
  };

  const hasHandle = (pair: string) => handlePairs.includes(pair);

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
          <button
            className={showChat ? "active" : ""}
            onClick={onToggleChat}
            title="Toggle Chat"
          >
            <img src={icon("message-square-text")} alt="" />
          </button>
          <hr />
          <button
            className={active("knowledge", leftPanel)}
            onClick={() => onLeftPanel("knowledge")}
            title="Knowledge Base"
          >
            <img src={icon("book")} alt="" />
          </button>
          <button
            className={active("history", leftPanel)}
            onClick={() => onLeftPanel("history")}
            title="History"
          >
            <img src={icon("history")} alt="" />
          </button>
          <button
            className={active("llm_settings", leftPanel)}
            onClick={() => onLeftPanel("llm_settings")}
            title="LLM Settings"
          >
            <img src={icon("settings-2")} alt="" />
          </button>
          <div className="flex-spacer" />
          <button
            className={ttsOn ? "active" : ""}
            onClick={onToggleTts}
            title="Text to Speech"
          >
            <img src={icon("speaker")} alt="TTS" />
          </button>
          <button
            className={sttOn ? "active" : ""}
            onClick={onToggleStt}
            title="Speech to Text"
          >
            <img src={icon("mic")} alt="STT" />
          </button>
        </div>

        {/* ── Panels container (flex:1 so it fills remaining space,
            keeping the right icon bar flush at the far right). ── */}
        <div
          ref={panelsRef}
          style={{ flex: 1, display: "flex", overflow: "hidden", minWidth: 0 }}
        >
          {/* ── Left panel ── */}
          <div
            className={
              leftPanel ? "collapsible-panel left" : "panel-hidden"
            }
            style={{ width: leftPanelW }}
          >
            {leftPanel === "knowledge" && <KnowledgeBasePanel />}
            {leftPanel === "history" && (
              <ChatHistoryPanel
                onSelectConversation={onSelectConversation}
              />
            )}
            {leftPanel === "llm_settings" && <LLMSettingsPanel />}
          </div>

          {/* ── Handle: left ↔ (chat|canvas|right) ── */}
          {hasHandle("left-chat") && makeHandle("left-chat")}
          {hasHandle("left-canvas") && makeHandle("left-canvas")}
          {hasHandle("left-right") && makeHandle("left-right")}

          {/* ── Chat panel ── */}
          <div
            className={showChat ? "chat-panel" : "panel-hidden"}
            style={{ width: chatW, flex: "none" }}
          >
            {showChat && children}
          </div>

          {/* ── Handle: chat ↔ (canvas|right) ── */}
          {hasHandle("chat-canvas") && makeHandle("chat-canvas")}
          {hasHandle("chat-right") && makeHandle("chat-right")}

          {/* ── Canvas panel (canvas viewer + art-prompt) ── */}
          <div
            className={showCanvas ? "canvas-panel" : "panel-hidden"}
            style={{ width: canvasW, flex: "none" }}
          >
            {showCanvas && (
              <>
                <CanvasPanel />
                <div className="art-prompt-panel">
                  <ArtPromptPanel />
                </div>
              </>
            )}
          </div>

          {/* ── Handle: canvas ↔ right ── */}
          {hasHandle("canvas-right") && makeHandle("canvas-right")}

          {/* ── Right panel ── */}
          <div
            className={
              rightPanel ? "collapsible-panel right" : "panel-hidden"
            }
            style={{ width: rightPanelW }}
          >
            {rightPanel === "art_model" && <ArtModelPanel />}
            {rightPanel === "lora" && <LoraPanel />}
            {rightPanel === "embeddings" && <EmbeddingsPanel />}
            {rightPanel === "layers" && <LayersPanel />}
            {rightPanel === "grid" && <GridPanel />}
            {rightPanel === "image_browser" && <ImageBrowserPanel />}
            {rightPanel === "stats" && <StatsPanel />}
          </div>
        </div>

        {/* ── Right icon bar (direct child of main-row, anchored to
            the far right edge because panels container fills flex:1) ── */}
        <div className="icon-bar right">
          <button
            className={showCanvas ? "active" : ""}
            onClick={onToggleCanvas}
            title="Canvas"
          >
            <img src={icon("image")} alt="Canvas" />
          </button>
          <hr />
          <button
            className={active("art_model", rightPanel)}
            onClick={() => onRightPanel("art_model")}
            title="Art Model"
          >
            <img src={icon("sparkles")} alt="Model" />
          </button>
          <button
            className={active("lora", rightPanel)}
            onClick={() => onRightPanel("lora")}
            title="LoRA"
          >
            <img src={icon("puzzle")} alt="LoRA" />
          </button>
          <button
            className={active("embeddings", rightPanel)}
            onClick={() => onRightPanel("embeddings")}
            title="Embeddings"
          >
            <img src={icon("scan-text")} alt="Embeddings" />
          </button>
          <button
            className={active("layers", rightPanel)}
            onClick={() => onRightPanel("layers")}
            title="Layers"
          >
            <img src={icon("layers")} alt="Layers" />
          </button>
          <button
            className={active("grid", rightPanel)}
            onClick={() => onRightPanel("grid")}
            title="Grid"
          >
            <img src={icon("grid-2x2-check")} alt="Grid" />
          </button>
          <button
            className={active("image_browser", rightPanel)}
            onClick={() => onRightPanel("image_browser")}
            title="Image Browser"
          >
            <img src={icon("images")} alt="Browser" />
          </button>
          <button
            className={active("stats", rightPanel)}
            onClick={() => onRightPanel("stats")}
            title="Stats"
          >
            <img src={icon("activity")} alt="Stats" />
          </button>
          <div className="flex-spacer" />
          <button onClick={onOpenSettings} title="Settings">
            <img src={icon("settings")} alt="Settings" />
          </button>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="footer-bar">
        &copy; {new Date().getFullYear()} Capsize LLC &mdash; All rights
        reserved.
      </div>
    </div>
  );
}
