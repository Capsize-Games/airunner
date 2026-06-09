import LucideIcon from "../../shared/LucideIcon";

const BTN_GROUP_HEIGHT = 28;

interface MessageActionsProps {
  isUser: boolean;
  isEditing: boolean;
  onCopy: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onPlay?: () => void;
}

export default function MessageActions({
  isUser,
  isEditing,
  onCopy,
  onEdit,
  onDelete,
  onPlay,
}: MessageActionsProps) {
  if (isEditing) return null;

  return (
    <div
      className="message-actions"
      style={{ height: BTN_GROUP_HEIGHT, visibility: "hidden" }}
    >
      {isUser ? (
        <div
          className="d-flex justify-content-end align-items-center"
          style={{ height: "100%" }}
        >
          <div
            className="d-flex gap-1"
            style={{
              background: "rgba(0,0,0,0.4)",
              borderRadius: 4,
              padding: "2px 4px",
            }}
          >
            <button
              className="message-action-btn"
              onClick={onCopy}
              title="Copy message"
            >
              <LucideIcon name="copy" size={14} />
            </button>
            <button
              className="message-action-btn"
              onClick={onEdit}
              title="Edit message"
            >
              <LucideIcon name="pencil" size={14} />
            </button>
            <button
              className="message-action-btn"
              onClick={onDelete}
              title="Delete message"
            >
              <LucideIcon name="trash" size={14} />
            </button>
          </div>
        </div>
      ) : (
        <div
          className="d-flex justify-content-end align-items-center"
          style={{ height: "100%" }}
        >
          <div
            className="d-flex gap-1"
            style={{
              background: "rgba(0,0,0,0.4)",
              borderRadius: 4,
              padding: "2px 4px",
            }}
          >
            <button
              className="message-action-btn"
              onClick={onCopy}
              title="Copy message"
            >
              <LucideIcon name="copy" size={14} />
            </button>
            <button
              className="message-action-btn"
              onClick={onPlay}
              title="Play via TTS"
            >
              <LucideIcon name="play" size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
