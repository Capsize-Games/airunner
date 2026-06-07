import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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

  // ── Determine whether we are mid-stream ───────────────────────────
  // The stream buffers are non-empty only while streaming is active.
  // Once onDone fires the hook clears them; a stale non-empty buffer
  // after a completed turn would produce a duplicate "streaming" bubble.
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
  // Render messages in their natural array order so that user and
  // assistant turns appear interleaved correctly (Bug 2: user-first
  // grouping caused prior assistant replies to appear after the next
  // user message).
  //
  // If there is a completed assistant message with thinking_content,
  // its thinking block is rendered inline inside MessageBubble, so
  // there is no need to split the last assistant out.
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
          <MessageBubble key={item.key} message={item.msg} />
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
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {streamBuffer.trimStart()}
          </ReactMarkdown>
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
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {(message.content || "").trimStart()}
        </ReactMarkdown>
      </div>
    </div>
  );
}
