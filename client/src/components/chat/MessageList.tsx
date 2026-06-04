import { useState } from "react";
import type { Message } from "../../types/api";

export default function MessageList({
  messages,
  streamBuffer,
  thinkingBuffer,
}: {
  messages: Message[];
  streamBuffer?: string;
  thinkingBuffer?: string;
}) {
  const [thinkingExpanded, setThinkingExpanded] = useState(true);

  if (messages.length === 0 && !streamBuffer && !thinkingBuffer) {
    return (
      <div className="text-muted text-center mt-5">
        <p>Start a conversation by typing a message below.</p>
      </div>
    );
  }

  const userMessages = messages.filter((m) => m.role === "user");
  const assistantMessages = messages.filter(
    (m) => m.role === "assistant",
  );
  const lastAssistant =
    assistantMessages.length > 0
      ? assistantMessages[assistantMessages.length - 1]
      : null;
  const hasCompletedThinking =
    lastAssistant?.thinking_content != null;

  return (
    <div className="d-flex flex-column gap-2">
      {userMessages.map((msg, i) => (
        <MessageBubble key={`u-${i}`} message={msg} />
      ))}
      {assistantMessages
        .slice(0, hasCompletedThinking ? -1 : assistantMessages.length)
        .map((msg, i) => (
          <MessageBubble key={`a-${i}`} message={msg} />
        ))}
      {hasCompletedThinking && lastAssistant && (
        <MessageBubble key="a-last" message={lastAssistant} />
      )}
      {!hasCompletedThinking &&
        (thinkingBuffer || streamBuffer) && (
          <StreamingBubble
            thinkingBuffer={thinkingBuffer}
            streamBuffer={streamBuffer}
            thinkingExpanded={thinkingExpanded}
            onToggle={() => setThinkingExpanded((e) => !e)}
          />
        )}
    </div>
  );
}

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
      {streamBuffer && (
        <div
          className="streaming-cursor"
          style={{ color: "var(--theme-text)" }}
        >
          {streamBuffer.trimStart()}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const hasThinking = !!message.thinking_content;

  return (
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
      <div style={{ color: "var(--theme-text)" }}>
        {(message.content || "").trimStart()}
      </div>
    </div>
  );
}
