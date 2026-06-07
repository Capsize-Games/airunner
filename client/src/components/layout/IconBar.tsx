import LucideIcon from "../shared/LucideIcon";

type PanelId =
  | "image_browser"
  | "civitai_browser";

export function LeftIconBar({
  showChat,
  ttsOn,
  sttOn,
  onToggleChat,
  onToggleTts,
  onToggleStt,
  bottomSlot,
}: {
  showChat: boolean;
  ttsOn: boolean;
  sttOn: boolean;
  onToggleChat: () => void;
  onToggleTts: () => void;
  onToggleStt: () => void;
  bottomSlot?: React.ReactNode;
}) {
  return (
    <div className="icon-bar left">
      <button
        className={showChat ? "active" : ""}
        onClick={onToggleChat}
        title="Toggle Chat"
      >
        <LucideIcon name="bot-message-square" />
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
