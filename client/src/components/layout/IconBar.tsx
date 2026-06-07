import LucideIcon from "../shared/LucideIcon";

type PanelId =
  | "knowledge"
  | "history"
  | "llm_settings"
  | "lora"
  | "embeddings"
  | "image_browser"
  | "civitai_browser";

export function LeftIconBar({
  showChat,
  leftPanel,
  ttsOn,
  sttOn,
  onToggleChat,
  onLeftPanel,
  onToggleTts,
  onToggleStt,
  bottomSlot,
}: {
  showChat: boolean;
  leftPanel: PanelId | null;
  ttsOn: boolean;
  sttOn: boolean;
  onToggleChat: () => void;
  onLeftPanel: (id: PanelId) => void;
  onToggleTts: () => void;
  onToggleStt: () => void;
  bottomSlot?: React.ReactNode;
}) {
  const active = (id: PanelId, panel: PanelId | null) =>
    panel === id ? "active" : "";

  return (
    <div className="icon-bar left">
      <button
        className={showChat ? "active" : ""}
        onClick={onToggleChat}
        title="Toggle Chat"
      >
        <LucideIcon name="bot-message-square" />
      </button>
      <hr />
      <button
        className={active("knowledge", leftPanel)}
        onClick={() => onLeftPanel("knowledge")}
        title="Knowledge Base"
      >
        <LucideIcon name="book" />
      </button>
      <button
        className={active("history", leftPanel)}
        onClick={() => onLeftPanel("history")}
        title="History"
      >
        <LucideIcon name="history" />
      </button>
      <button
        className={active("llm_settings", leftPanel)}
        onClick={() => onLeftPanel("llm_settings")}
        title="LLM Settings"
      >
        <LucideIcon name="sliders-horizontal" />
      </button>
      <div className="flex-spacer" />
      <button
        className={ttsOn ? "active" : ""}
        onClick={onToggleTts}
        title="Text to Speech"
      >
        <LucideIcon name="speaker" />
      </button>
      <button
        className={sttOn ? "active" : ""}
        onClick={onToggleStt}
        title="Speech to Text"
      >
        <LucideIcon name="mic" />
      </button>
      {bottomSlot}
    </div>
  );
}

export function RightIconBar({
  showCanvas,
  rightPanel,
  onToggleCanvas,
  onRightPanel,
  onOpenSettings,
  showCacheDebug,
  onToggleCacheDebug,
  showStats,
  onToggleStats,
}: {
  showCanvas: boolean;
  rightPanel: PanelId | null;
  onToggleCanvas: () => void;
  onRightPanel: (id: PanelId) => void;
  onOpenSettings: () => void;
  showCacheDebug: boolean;
  onToggleCacheDebug: () => void;
  showStats: boolean;
  onToggleStats: () => void;
}) {
  const active = (id: PanelId, panel: PanelId | null) =>
    panel === id ? "active" : "";

  return (
    <div className="icon-bar right">
      <button
        className={showCanvas ? "active" : ""}
        onClick={onToggleCanvas}
        title="Canvas"
      >
        <LucideIcon name="image" />
      </button>
      <hr />
      <button
        className={active("civitai_browser", rightPanel)}
        onClick={() => onRightPanel("civitai_browser")}
        title="CivitAI Browser"
      >
        <LucideIcon name="cloud" />
      </button>
      <button
        className={active("lora", rightPanel)}
        onClick={() => onRightPanel("lora")}
        title="LoRA"
      >
        <LucideIcon name="puzzle" />
      </button>
      <button
        className={active("embeddings", rightPanel)}
        onClick={() => onRightPanel("embeddings")}
        title="Embeddings"
      >
        <LucideIcon name="scan-text" />
      </button>
      <button
        className={active("image_browser", rightPanel)}
        onClick={() => onRightPanel("image_browser")}
        title="Image Browser"
      >
        <LucideIcon name="images" />
      </button>
      <div className="flex-spacer" />
      <button
        className={showStats ? "active" : ""}
        onClick={onToggleStats}
        title="Stats"
      >
        <LucideIcon name="activity" />
      </button>
      <button
        className={showCacheDebug ? "active" : ""}
        onClick={onToggleCacheDebug}
        title="Cache Debug"
      >
        <LucideIcon name="database-zap" />
      </button>
      <button onClick={onOpenSettings} title="Settings">
        <LucideIcon name="settings" />
      </button>
    </div>
  );
}
