import LucideIcon from "../shared/LucideIcon";

type PanelId = "civitai_browser";

export function LeftIconBar({
  showChat,
  showCanvas,
  rightPanel,
  onToggleChat,
  onToggleCanvas,
  onRightPanel,
  onOpenSettings,
  bottomSlot,
}: {
  showChat: boolean;
  showCanvas: boolean;
  rightPanel: PanelId | null;
  onToggleChat: () => void;
  onToggleCanvas: () => void;
  onRightPanel: (id: PanelId) => void;
  onOpenSettings: () => void;
  bottomSlot?: React.ReactNode;
}) {
  const canvasActive = showCanvas && rightPanel !== "civitai_browser";
  const civitaiActive = rightPanel === "civitai_browser";

  return (
    <div className="icon-bar left">
      <button
        className={showChat ? "active" : ""}
        onClick={onToggleChat}
        title="Toggle Chat"
      >
        <LucideIcon name="bot-message-square" size={18} />
        <span className="icon-bar-label">Chat</span>
      </button>

      <button
        className={canvasActive ? "active" : ""}
        onClick={onToggleCanvas}
        title="Canvas"
      >
        <LucideIcon name="image" size={18} />
        <span className="icon-bar-label">Canvas</span>
      </button>

      <button
        className={civitaiActive ? "active" : ""}
        onClick={() => onRightPanel("civitai_browser")}
        title="CivitAI Browser"
      >
        <LucideIcon name="globe" size={18} />
        <span className="icon-bar-label">CivitAI</span>
      </button>

      <div className="flex-spacer" />

      <button onClick={onOpenSettings} title="Settings">
        <LucideIcon name="settings" size={18} />
        <span className="icon-bar-label">Settings</span>
      </button>

      {bottomSlot}
    </div>
  );
}
