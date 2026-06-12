import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../../../types/api";
import { parseToolCallContent } from "../toolCallUtils";
import MessageAvatar from "./MessageAvatar";
import ToolCallSection from "./ToolCallSection";
import MessageActions from "./MessageActions";

interface MessageBubbleProps {
  message: Message;
  index: number;
  editingIndex: number | null;
  editContent: string;
  onStartEdit: (index: number, content: string) => void;
  onCancelEdit: () => void;
  onConfirmEdit: () => void;
  onEditContentChange: (value: string) => void;
  onEditKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onDelete?: (index: number) => void;
  onCopy?: (content: string) => void;
  onPlay?: (content: string) => void;
  botName?: string;
  userName?: string;
}

export default function MessageBubble({
  message,
  index,
  editingIndex,
  editContent,
  onStartEdit,
  onCancelEdit,
  onConfirmEdit,
  onEditContentChange,
  onEditKeyDown,
  onDelete,
  onCopy,
  onPlay,
  botName = "AI",
  userName = "You",
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const hasThinking = !isUser && !!(message.thinking_content?.trim());
  const isEditing = editingIndex === index;

  const { toolCalls, cleanContent } = parseToolCallContent(message.content);
  const hasToolCalls = toolCalls.length > 0;

  const handleCopy = useCallback(
    () => onCopy?.(message.content),
    [onCopy, message.content],
  );
  const handleDelete = useCallback(
    () => onDelete?.(index),
    [onDelete, index],
  );
  const handlePlay = useCallback(
    () => onPlay?.(message.content),
    [onPlay, message.content],
  );
  const handleEditClick = useCallback(
    () => onStartEdit(index, message.content),
    [onStartEdit, index, message.content],
  );

  return (
    <div className="message-bubble">
      <div
        className="p-2 rounded w-100"
        style={{
          position: "relative",
          whiteSpace: "pre-wrap",
          background: isUser
            ? "rgba(0,132,185,0.15)"
            : "rgba(71,0,129,0.15)",
          border: isUser
            ? "1px solid rgba(0,132,185,0.3)"
            : "1px solid rgba(71,0,129,0.2)",
        }}
      >
        <MessageAvatar isUser={isUser} label={isUser ? userName : botName} />

        {hasThinking && (
          <div
            className="mb-2 rounded"
            style={{
              background: "rgba(0,132,185,0.08)",
              border: "1px solid rgba(0,132,185,0.15)",
              fontSize: "0.85rem",
              color: "#888",
            }}
          >
            <div
              className="d-flex align-items-center gap-1 p-1 cursor-pointer user-select-none"
              onClick={() => setThinkingExpanded((e) => !e)}
              role="button"
            >
              <span>{thinkingExpanded ? "▼" : "▶"}</span>
              <span>✅</span>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "var(--theme-text-secondary)",
                }}
              >
                Complete
              </span>
            </div>
            {thinkingExpanded && (
              <div
                className="p-2"
                style={{
                  whiteSpace: "pre-wrap",
                  fontStyle: "italic",
                  maxHeight: 300,
                  overflowY: "auto",
                }}
              >
                {message.thinking_content}
              </div>
            )}
          </div>
        )}

        {hasToolCalls &&
          toolCalls.map((tc, i) => <ToolCallSection key={i} toolCall={tc} />)}

        {isEditing ? (
          <div>
            <textarea
              className="form-control"
              value={editContent}
              onChange={(e) => onEditContentChange(e.target.value)}
              onKeyDown={onEditKeyDown}
              rows={3}
              style={{
                resize: "none",
                background: "var(--theme-input-bg)",
                color: "var(--theme-text)",
                borderColor: "var(--theme-input-border)",
                fontSize: "0.85rem",
              }}
              autoFocus
            />
            <div className="d-flex gap-1 mt-1 justify-content-end">
              <button
                className="btn btn-sm btn-outline-secondary p-1"
                onClick={onCancelEdit}
                title="Cancel"
                style={{
                  height: 24,
                  border: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  fontSize: "0.75rem",
                }}
              >
                Cancel
              </button>
              <button
                className="btn btn-sm btn-outline-primary p-1"
                onClick={onConfirmEdit}
                disabled={!editContent.trim()}
                title="Save"
                style={{
                  height: 24,
                  border: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  fontSize: "0.75rem",
                }}
              >
                Save & Send
              </button>
            </div>
          </div>
        ) : (
          <div style={{ color: "var(--theme-text)" }}>
            {hasToolCalls && cleanContent ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {cleanContent.trimStart()}
              </ReactMarkdown>
            ) : !hasToolCalls ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {(message.content || "").trimStart()}
              </ReactMarkdown>
            ) : null}
          </div>
        )}

        <MessageActions
          isUser={isUser}
          isEditing={isEditing}
          onCopy={handleCopy}
          onEdit={handleEditClick}
          onDelete={handleDelete}
          onPlay={handlePlay}
        />
      </div>
    </div>
  );
}
