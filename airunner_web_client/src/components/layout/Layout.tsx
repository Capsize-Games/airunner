import type { ReactNode } from "react";

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
  showCanvas: boolean;
  onToggleCanvas: () => void;
  showArtPrompt: boolean;
  onToggleArtPrompt: () => void;
  ttsOn: boolean;
  onToggleTts: () => void;
  sttOn: boolean;
  onToggleStt: () => void;
  onOpenSettings: () => void;
}

const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

export default function Layout({
  children,
  leftPanel,
  onLeftPanel,
  rightPanel,
  onRightPanel,
  showCanvas,
  onToggleCanvas,
  showArtPrompt,
  onToggleArtPrompt,
  ttsOn,
  onToggleTts,
  sttOn,
  onToggleStt,
  onOpenSettings,
}: LayoutProps) {
  const active = (id: PanelId, panel: PanelId | null) =>
    panel === id ? "active" : "";

  return (
    <div className="app-shell">
      {/* ── Top bar ── */}
      <div className="topbar">
        <div className="topbar-logo">
          🎨 AI <span>Runner</span>
        </div>
      </div>

      {/* ── Main row ── */}
      <div className="main-row">
        {/* ── Left icon bar ── */}
        <div className="icon-bar left">
          <button
            title="Chat"
            onClick={() => onLeftPanel("chat" as PanelId)}
          >
            <img src={icon("message-square-heart")} alt="" />
          </button>
          <hr />
          <button
            className={active("knowledge", leftPanel)}
            onClick={() => onLeftPanel("knowledge")}
            title="Knowledge Base"
          >
            <img src={icon("book-open")} alt="" />
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

        {/* ── Left collapsible panel ── */}
        <div
          className={
            leftPanel
              ? "collapsible-panel left"
              : "panel-hidden"
          }
        >
          {leftPanel === "knowledge" && (
            <div className="p-2">
              <h6 className="text-muted">Knowledge Base</h6>
              <p className="muted-text">Knowledge content will appear here.</p>
            </div>
          )}
          {leftPanel === "history" && (
            <div className="p-2">
              <h6 className="text-muted">Chat History</h6>
              <p className="muted-text">History content will appear here.</p>
            </div>
          )}
          {leftPanel === "llm_settings" && (
            <div className="p-2">
              <h6 className="text-muted">LLM Settings</h6>
              <p className="muted-text">Settings content will appear here.</p>
            </div>
          )}
        </div>

        {/* ── Center ── */}
        <div className="center-content">
          {/* Chat panel (always visible) */}
          <div className="chat-panel">{children}</div>

          {/* Canvas panel (toggled) */}
          {showCanvas && (
            <div className="canvas-panel">
              <span className="text-muted">Canvas</span>
            </div>
          )}

          {/* Art prompt panel (toggled) */}
          {showArtPrompt && (
            <div className="art-prompt-panel p-2">
              <h6>Art Prompt</h6>
            </div>
          )}
        </div>

        {/* ── Right collapsible panel ── */}
        <div
          className={
            rightPanel
              ? "collapsible-panel right"
              : "panel-hidden"
          }
        >
          {rightPanel === "art_model" && (
            <div className="p-2">
              <h6 className="text-muted">Art Model</h6>
              <p className="muted-text">Model settings will appear here.</p>
            </div>
          )}
          {rightPanel === "lora" && (
            <div className="p-2">
              <h6 className="text-muted">LoRA</h6>
              <p className="muted-text">LoRA settings will appear here.</p>
            </div>
          )}
          {rightPanel === "embeddings" && (
            <div className="p-2">
              <h6 className="text-muted">Embeddings</h6>
              <p className="muted-text">Embeddings will appear here.</p>
            </div>
          )}
          {rightPanel === "layers" && (
            <div className="p-2">
              <h6 className="text-muted">Layers</h6>
              <p className="muted-text">Layer controls will appear here.</p>
            </div>
          )}
          {rightPanel === "grid" && (
            <div className="p-2">
              <h6 className="text-muted">Grid Settings</h6>
              <p className="muted-text">Grid settings will appear here.</p>
            </div>
          )}
          {rightPanel === "image_browser" && (
            <div className="p-2">
              <h6 className="text-muted">Image Browser</h6>
              <p className="muted-text">Image browser will appear here.</p>
            </div>
          )}
          {rightPanel === "stats" && (
            <div className="p-2">
              <h6 className="text-muted">Model Resources</h6>
              <p className="muted-text">Stats will appear here.</p>
            </div>
          )}
        </div>

        {/* ── Right icon bar ── */}
        <div className="icon-bar right">
          <button
            className={showCanvas ? "active" : ""}
            onClick={onToggleCanvas}
            title="Canvas"
          >
            <img src={icon("image")} alt="Canvas" />
          </button>
          <button
            className={showArtPrompt ? "active" : ""}
            onClick={onToggleArtPrompt}
            title="Prompt Editor"
          >
            <img src={icon("message-square-heart")} alt="Prompt" />
          </button>
          <hr />
          <button
            className={active("art_model", rightPanel)}
            onClick={() => onRightPanel("art_model")}
            title="Art Model"
          >
            <img src={icon("box")} alt="Model" />
          </button>
          <button
            className={active("lora", rightPanel)}
            onClick={() => onRightPanel("lora")}
            title="LoRA"
          >
            <img src={icon("layers-2")} alt="LoRA" />
          </button>
          <button
            className={active("embeddings", rightPanel)}
            onClick={() => onRightPanel("embeddings")}
            title="Embeddings"
          >
            <img src={icon("tag")} alt="Embeddings" />
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
            <img src={icon("grid-3x3")} alt="Grid" />
          </button>
          <button
            className={active("image_browser", rightPanel)}
            onClick={() => onRightPanel("image_browser")}
            title="Image Browser"
          >
            <img src={icon("folder-open")} alt="Browser" />
          </button>
          <button
            className={active("stats", rightPanel)}
            onClick={() => onRightPanel("stats")}
            title="Stats"
          >
            <img src={icon("bar-chart-3")} alt="Stats" />
          </button>
          <div className="flex-spacer" />
          <button onClick={onOpenSettings} title="Settings">
            <img src={icon("settings")} alt="Settings" />
          </button>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="footer-bar">
        © {new Date().getFullYear()} AI Runner — All rights reserved.
      </div>
    </div>
  );
}
