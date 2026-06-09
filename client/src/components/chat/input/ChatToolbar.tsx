import ModelSelector from "../ModelSelector";
import LucideIcon from "../../shared/LucideIcon";
import ToolbarToggle from "../shared/ToolbarToggle";

interface ChatToolbarProps {
  ttsOn: boolean;
  sttOn: boolean;
  onToggleTts?: () => void;
  onToggleStt?: () => void;
  streaming: boolean;
  input: string;
  handleSend: () => Promise<void>;
  handleCancel: () => void;
  handleNewConversation: () => Promise<void>;
}

export default function ChatToolbar({
  ttsOn,
  sttOn,
  onToggleTts,
  onToggleStt,
  streaming,
  input,
  handleSend,
  handleCancel,
  handleNewConversation,
}: ChatToolbarProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 2,
        padding: "3px 4px",
        borderTop: "1px solid rgba(255,255,255,0.08)",
        flexShrink: 0,
      }}
    >
      <button
        type="button"
        onClick={handleNewConversation}
        title="New conversation"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 26,
          height: 26,
          padding: 0,
          background: "transparent",
          border: "none",
          cursor: "pointer",
          borderRadius: 4,
          color: "rgba(255,255,255,0.45)",
          flexShrink: 0,
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.color =
            "rgba(255,255,255,0.85)";
          (e.currentTarget as HTMLButtonElement).style.background =
            "rgba(255,255,255,0.08)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.color =
            "rgba(255,255,255,0.45)";
          (e.currentTarget as HTMLButtonElement).style.background =
            "transparent";
        }}
      >
        <LucideIcon name="plus" size={15} />
      </button>

      <span
        style={{
          width: 1,
          height: 14,
          background: "rgba(255,255,255,0.12)",
          flexShrink: 0,
        }}
      />

      <ModelSelector />

      <ToolbarToggle
        active={ttsOn}
        title="Text to Speech"
        onClick={onToggleTts}
        icon="speaker"
      />

      <ToolbarToggle
        active={sttOn}
        title="Speech to Text"
        onClick={onToggleStt}
        icon="mic"
      />

      {streaming ? (
        <button
          type="button"
          onClick={handleCancel}
          title="Cancel"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            padding: 0,
            background: "var(--bs-danger)",
            border: "none",
            cursor: "pointer",
            borderRadius: 5,
            flexShrink: 0,
          }}
        >
          <LucideIcon name="circle-x" size={15} />
        </button>
      ) : (
        <button
          type="button"
          onClick={handleSend}
          disabled={!input.trim()}
          title="Send message"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 28,
            height: 28,
            padding: 0,
            background: input.trim()
              ? "var(--bs-primary)"
              : "rgba(255,255,255,0.1)",
            border: "none",
            cursor: input.trim() ? "pointer" : "default",
            borderRadius: 5,
            flexShrink: 0,
          }}
        >
          <LucideIcon name="chevron-up" size={15} />
        </button>
      )}
    </div>
  );
}
