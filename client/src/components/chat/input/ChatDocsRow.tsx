import type { ChatPanel } from "../types";
import LucideIcon from "../../shared/LucideIcon";
import PanelIconBtn from "../shared/PanelIconBtn";

interface ChatDocsRowProps {
  openPanel: ChatPanel;
  togglePanel: (panel: NonNullable<ChatPanel>) => void;
  docCount: number;
}

export default function ChatDocsRow({
  openPanel,
  togglePanel,
  docCount,
}: ChatDocsRowProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "3px 6px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        flexShrink: 0,
        gap: 4,
      }}
    >
      <button
        type="button"
        onClick={() => togglePanel("knowledge")}
        title="Knowledge base"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 5,
          background:
            openPanel === "knowledge"
              ? "rgba(255,255,255,0.08)"
              : "transparent",
          border: "none",
          cursor: "pointer",
          padding: "2px 5px",
          borderRadius: 4,
          color:
            openPanel === "knowledge"
              ? "var(--bs-primary)"
              : "rgba(255,255,255,0.4)",
          fontSize: "0.72rem",
        }}
        onMouseEnter={(e) => {
          if (openPanel !== "knowledge")
            (e.currentTarget as HTMLButtonElement).style.background =
              "rgba(255,255,255,0.06)";
        }}
        onMouseLeave={(e) => {
          if (openPanel !== "knowledge")
            (e.currentTarget as HTMLButtonElement).style.background =
              "transparent";
        }}
      >
        <LucideIcon name="book" size={12} />
        <span>
          {docCount} Active document{docCount !== 1 ? "s" : ""}
        </span>
      </button>

      <span style={{ flex: 1 }} />

      <PanelIconBtn
        icon="history"
        title="Chat history"
        active={openPanel === "history"}
        onClick={() => togglePanel("history")}
      />
    </div>
  );
}
