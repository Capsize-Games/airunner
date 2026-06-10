import { useState, useCallback } from "react";
import LucideIcon from "../../shared/LucideIcon";

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
  const [copied, setCopied] = useState(false);

  if (isEditing) return null;

  const handleCopy = useCallback(() => {
    onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  }, [onCopy]);

  return (
    <div className="message-actions">
      <div
        className="d-flex gap-1"
        style={{
          background: "rgba(0,0,0,0.4)",
          borderRadius: 4,
          padding: "2px 4px",
        }}
      >
        <div className="message-action-btn-wrapper">
          <button
            className="message-action-btn"
            onClick={handleCopy}
            title="Copy message"
          >
            <LucideIcon name="copy" size={14} />
          </button>
          {copied && <span className="copy-toast">Copied!</span>}
        </div>
        {isUser ? (
          <>
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
          </>
        ) : (
          <button
            className="message-action-btn"
            onClick={onPlay}
            title="Play via TTS"
          >
            <LucideIcon name="play" size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
