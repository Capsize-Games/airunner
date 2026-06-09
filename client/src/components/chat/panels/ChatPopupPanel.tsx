import type { ChatPanel } from "../types";
import { KnowledgeBasePanel } from "../../panels/KnowledgeBasePanel";
import { ChatHistoryPanel } from "../../panels/ChatHistoryPanel";

interface ChatPopupPanelProps {
  openPanel: ChatPanel;
  popupAnchor: {
    left: number;
    bottom: number;
    width: number;
    height: number;
  } | null;
  onSelectConversation?: (id: number) => void;
  onClose: () => void;
}

export default function ChatPopupPanel({
  openPanel,
  popupAnchor,
  onSelectConversation,
  onClose,
}: ChatPopupPanelProps) {
  if (!openPanel || !popupAnchor) return null;

  return (
    <div
      id="chat-panel-popup"
      style={{
        position: "fixed",
        left: popupAnchor.left,
        bottom: popupAnchor.bottom,
        width: Math.max(popupAnchor.width, 360),
        height: popupAnchor.height,
        zIndex: 1300,
        background: "var(--theme-panel-bg)",
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 0,
        boxShadow: "4px -4px 24px rgba(0,0,0,0.7)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {openPanel === "knowledge" && <KnowledgeBasePanel />}
      {openPanel === "history" && (
        <ChatHistoryPanel
          onSelectConversation={(id) => {
            onSelectConversation?.(id);
            onClose();
          }}
        />
      )}
    </div>
  );
}
