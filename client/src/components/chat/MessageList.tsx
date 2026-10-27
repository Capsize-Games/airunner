import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../../types/api";
import LucideIcon from "../shared/LucideIcon";
import {
  parseToolCallContent,
  hasPartialToolCall,
  extractPartialToolCall,
  type ParsedToolCall,
} from "./toolCallUtils";

export default function MessageList({
  messages,
  streamBuffer,
  thinkingBuffer,
  onDeleteMessage,
  onSubmitEdit,
  onCopyMessage,
  onPlayMessage,
}: {
  messages: Message[];
  streamBuffer?: string;
  thinkingBuffer?: string;
  onDeleteMessage?: (index: number) => void;
  onSubmitEdit?: (index: number, newContent: string) => void;
  onCopyMessage?: (content: string) => void;
  onPlayMessage?: (content: string) => void;
}) {
  const [thinkingExpanded, setThinkingExpanded] = useState(true);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");

  // ── Hooks MUST be called before any early return ─────────────────
  const handleStartEdit = useCallback((index: number, content: string) => {
    setEditingIndex(index);
    setEditContent(content);
  }, []);

  const handleCancelEdit = useCallback(() => {
    setEditingIndex(null);
    setEditContent("");
  }, []);

  const handleConfirmEdit = useCallback(() => {
    if (editingIndex === null || !editContent.trim()) return;
    onSubmitEdit?.(editingIndex, editContent.trim());
    setEditingIndex(null);
    setEditContent("");
  }, [editingIndex, editContent, onSubmitEdit]);

  const handleEditKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleConfirmEdit();
      }
      if (e.key === "Escape") {
        handleCancelEdit();
      }
    },
    [handleConfirmEdit, handleCancelEdit],
  );

  // ── Determine whether we are mid-stream ───────────────────────────
  const isStreaming = !!(
    (thinkingBuffer && thinkingBuffer.length > 0) ||
    (streamBuffer && streamBuffer.length > 0)
  );

  // ── When nothing at all is shown, render the placeholder ───────────
  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="text-muted text-center mt-5">
        <p>Start a conversation by typing a message below.</p>
      </div>
    );
  }

  // ── Build an ordered render plan ──────────────────────────────────
  type RenderEntry =
    | { type: "message"; msg: Message; key: string }
    | { type: "streaming"; key: string };
  const rendered: RenderEntry[] = messages.map((msg, i) => ({
    type: "message" as const,
    msg,
    key: `msg-${i}`,
  }));

  if (isStreaming) {
    rendered.push({ type: "streaming" as const, key: "streaming" });
  }

  return (
    <div className="d-flex flex-column gap-2">
      {rendered.map((item) =>
        item.type === "message" ? (
          <MessageBubble
            key={item.key}
            message={item.msg}
            index={messages.indexOf(item.msg)}
            editingIndex={editingIndex}
            editContent={editContent}
            onStartEdit={handleStartEdit}
            onCancelEdit={handleCancelEdit}
            onConfirmEdit={handleConfirmEdit}
            onEditContentChange={setEditContent}
            onEditKeyDown={handleEditKeyDown}
            onDelete={onDeleteMessage}
            onCopy={onCopyMessage}
            onPlay={onPlayMessage}
          />
        ) : (
          <StreamingBubble
            key={item.key}
            thinkingBuffer={thinkingBuffer}
            streamBuffer={streamBuffer}
            thinkingExpanded={thinkingExpanded}
            onToggle={() => setThinkingExpanded((e) => !e)}
          />
        ),
      )}
    </div>
  );
}

// ── Shared collapsible section for tool calls ──────────────────────────────

function ToolCallSection({
  toolCall,
  defaultExpanded,
}: {
  toolCall: ParsedToolCall;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded ?? false);

  return (
    <div
      className="mb-2 rounded"
      style={{
        background: "rgba(180,90,0,0.08)",
        border: "1px solid rgba(180,90,0,0.15)",
        fontSize: "0.85rem",
        color: "#888",
      }}
    >
      <div
        className="d-flex align-items-center gap-1 p-1"
        style={{ cursor: "pointer", userSelect: "none" }}
        onClick={() => setExpanded((e) => !e)}
        role="button"
      >
        <span>{expanded ? "▼" : "▶"}</span>
        <span>🔧</span>
        <span style={{ fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}>
          Tool Call: {toolCall.functionName}
        </span>
      </div>
      {expanded && (
        <div className="p-2" style={{ whiteSpace: "pre-wrap", maxHeight: 300, overflowY: "auto" }}>
          {Object.entries(toolCall.parameters).map(([key, value]) => (
            <div key={key} style={{ marginBottom: 4 }}>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: "0.75rem",
                  color: "var(--theme-text-secondary)",
                  marginBottom: 2,
                }}
              >
                {key}
              </div>
              <div
                style={{
                  background: "rgba(0,0,0,0.1)",
                  borderRadius: 4,
                  padding: "4px 8px",
                  fontSize: "0.8rem",
                  color: "var(--theme-text)",
                }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Streaming bubble ──────────────────────────────────────────────────────

function StreamingBubble({
  thinkingBuffer,
  streamBuffer,
  thinkingExpanded,
  onToggle,
}: {
  thinkingBuffer?: string;
  streamBuffer?: string;
  thinkingExpanded: boolean;
  onToggle: () => void;
}) {
  // Parse tool calls from the streaming buffer
  let toolCalls: ParsedToolCall[] = [];
  let cleanContent = streamBuffer ?? "";
  const hasPartial = streamBuffer ? hasPartialToolCall(streamBuffer) : false;
  let partialToolCall = "";

  if (streamBuffer) {
    const result = parseToolCallContent(streamBuffer);
    toolCalls = result.toolCalls;
    cleanContent = result.cleanContent;

    if (hasPartial) {
      partialToolCall = extractPartialToolCall(streamBuffer);
    }
  }

  return (
    <div
      className="p-2 rounded w-100"
      style={{
        background: "rgba(71,0,129,0.15)",
        border: "1px solid rgba(71,0,129,0.2)",
      }}
    >
      <small
        className="fw-bold d-block mb-1"
        style={{ color: "var(--theme-text-secondary)" }}
      >
        AI
      </small>

      {/* Thinking section */}
      {thinkingBuffer && (
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
            className="d-flex align-items-center gap-1 p-1"
            style={{ cursor: "pointer", userSelect: "none" }}
            onClick={onToggle}
            role="button"
          >
            <span>{thinkingExpanded ? "▼" : "▶"}</span>
            <span>🧠</span>
            <span style={{ fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}>
              Thinking
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
              {thinkingBuffer}
            </div>
          )}
        </div>
      )}

      {/* Tool call sections (complete) */}
      {toolCalls.map((tc, i) => (
        <ToolCallSection key={i} toolCall={tc} defaultExpanded={true} />
      ))}

      {/* Partial tool call (streaming, not yet closed) */}
      {partialToolCall && (
        <div
          className="mb-2 rounded"
          style={{
            background: "rgba(180,90,0,0.08)",
            border: "1px solid rgba(180,90,0,0.15)",
            fontSize: "0.85rem",
            color: "#888",
          }}
        >
          <div className="d-flex align-items-center gap-1 p-1">
            <span>🔧</span>
            <span style={{ fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}>
              Tool Call (streaming...)
            </span>
          </div>
          <div
            className="p-2"
            style={{
              whiteSpace: "pre-wrap",
              fontStyle: "italic",
              maxHeight: 300,
              overflowY: "auto",
            }}
          >
            {partialToolCall}
          </div>
        </div>
      )}

      {/* Clean visible content */}
      {cleanContent && (
        <div
          className="streaming-cursor"
          style={{ color: "var(--theme-text)" }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {cleanContent.trimStart()}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
}

// ── Stored message bubble ─────────────────────────────────────────────────

const BTN_GROUP_HEIGHT = 28;

function MessageBubble({
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
}: {
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
}) {
  const isUser = message.role === "user";
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const hasThinking = !!message.thinking_content;

  // Parse tool calls from message content
  const { toolCalls, cleanContent } = parseToolCallContent(message.content);
  const hasToolCalls = toolCalls.length > 0;

  const isEditing = editingIndex === index;

  const handleCopy = useCallback(() => {
    onCopy?.(message.content);
  }, [onCopy, message.content]);

  const handleDelete = useCallback(() => {
    onDelete?.(index);
  }, [onDelete, index]);

  const handlePlay = useCallback(() => {
    onPlay?.(message.content);
  }, [onPlay, message.content]);

  const handleEditClick = useCallback(() => {
    onStartEdit(index, message.content);
  }, [onStartEdit, index, message.content]);

  return (
    <div className="message-bubble">
      <div
        className="p-2 rounded w-100"
        style={{
          whiteSpace: "pre-wrap",
          background: isUser
            ? "rgba(0,132,185,0.15)"
            : "rgba(71,0,129,0.15)",
          border: isUser
            ? "1px solid rgba(0,132,185,0.3)"
            : "1px solid rgba(71,0,129,0.2)",
        }}
      >
        <small
          className="fw-bold d-block mb-1"
          style={{ color: "var(--theme-text-secondary)" }}
        >
          {isUser ? "You" : "AI"}
        </small>

        {/* Thinking section */}
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
              className="d-flex align-items-center gap-1 p-1"
              style={{ cursor: "pointer", userSelect: "none" }}
              onClick={() => setThinkingExpanded((e) => !e)}
              role="button"
            >
              <span>{thinkingExpanded ? "▼" : "▶"}</span>
              <span>✅</span>
              <span style={{ fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}>
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

        {/* Tool call sections */}
        {hasToolCalls &&
          toolCalls.map((tc, i) => (
            <ToolCallSection key={i} toolCall={tc} />
          ))}

        {/* Main content */}
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
      </div>

      {/* ── Action buttons ── */}
      {!isEditing && (
        <div
          className="message-actions"
          style={{
            height: BTN_GROUP_HEIGHT,
            visibility: "hidden",
          }}
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
                  onClick={handleCopy}
                  title="Copy message"
                >
                  <LucideIcon name="copy" size={14} />
                </button>
                <button
                  className="message-action-btn"
                  onClick={handleEditClick}
                  title="Edit message"
                >
                  <LucideIcon name="pencil" size={14} />
                </button>
                <button
                  className="message-action-btn"
                  onClick={handleDelete}
                  title="Delete message"
                >
                  <LucideIcon name="trash" size={14} />
                </button>
              </div>
            </div>
          ) : (
            <div
              className="d-flex justify-content-start align-items-center"
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
                  onClick={handleCopy}
                  title="Copy message"
                >
                  <LucideIcon name="copy" size={14} />
                </button>
                <button
                  className="message-action-btn"
                  onClick={handlePlay}
                  title="Play via TTS"
                >
                  <LucideIcon name="play" size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
