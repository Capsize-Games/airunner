import { useState } from "react";
import type { ParsedToolCall } from "../toolCallUtils";

export default function ToolCallSection({
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
        className="d-flex align-items-center gap-1 p-1 cursor-pointer user-select-none"
        onClick={() => setExpanded((e) => !e)}
        role="button"
      >
        <span>{expanded ? "▼" : "▶"}</span>
        <span>🔧</span>
        <span className="text-theme-secondary" style={{ fontSize: "0.75rem" }}>
          Tool Call: {toolCall.functionName}
        </span>
      </div>
      {expanded && (
        <div
          className="p-2"
          style={{ whiteSpace: "pre-wrap", maxHeight: 300, overflowY: "auto" }}
        >
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
