import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  parseToolCallContent,
  hasPartialToolCall,
  extractPartialToolCall,
} from "../toolCallUtils";
import MessageAvatar from "./MessageAvatar";
import ToolCallSection from "./ToolCallSection";

interface StreamingBubbleProps {
  thinkingBuffer?: string;
  streamBuffer?: string;
}

export default function StreamingBubble({
  thinkingBuffer,
  streamBuffer,
}: StreamingBubbleProps) {
  const [thinkingExpanded, setThinkingExpanded] = useState(true);

  let cleanContent = streamBuffer ?? "";
  const hasPartial = streamBuffer ? hasPartialToolCall(streamBuffer) : false;
  let partialToolCall = "";
  const toolCalls = streamBuffer
    ? (() => {
        const result = parseToolCallContent(streamBuffer);
        cleanContent = result.cleanContent;
        return result.toolCalls;
      })()
    : [];

  if (hasPartial && streamBuffer) {
    partialToolCall = extractPartialToolCall(streamBuffer);
  }

  return (
    <div
      className="p-2 rounded w-100"
      style={{
        background: "rgba(71,0,129,0.15)",
        border: "1px solid rgba(71,0,129,0.2)",
      }}
    >
      <MessageAvatar isUser={false} label="AI" />

      {thinkingBuffer?.trim() && (
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
            <span>🧠</span>
            <span
              style={{ fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}
            >
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

      {toolCalls.map((tc, i) => (
        <ToolCallSection key={i} toolCall={tc} defaultExpanded={true} />
      ))}

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
            <span
              style={{ fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}
            >
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
