import { useState } from "react";
import Spinner from "react-bootstrap/Spinner";
import LucideIcon from "../shared/LucideIcon";
import { useConversations } from "../../hooks/useConversations";

export function ChatHistoryPanel({
  onSelectConversation,
}: {
  onSelectConversation: (id: number) => void;
}) {
  const { conversations, loading, remove } = useConversations();
  const [confirmDeleteAll, setConfirmDeleteAll] = useState(false);

  const handleDeleteAll = () => {
    conversations.forEach((c) => remove(c.id));
    setConfirmDeleteAll(false);
  };

  return (
    <div className="d-flex flex-column h-100">
      {/* Sticky header */}
      <div
        className="flex-shrink-0 d-flex align-items-center justify-content-between bg-theme-panel border-b-theme"
        style={{ padding: "8px 12px 6px", gap: 8 }}
      >
        <span className="text-panel-label text-uppercase">
          Chat History
        </span>

        {confirmDeleteAll ? (
          <div className="d-flex align-items-center" style={{ gap: 4 }}>
            <span className="text-theme-secondary" style={{ fontSize: "0.7rem" }}>
              Delete all?
            </span>
            <button
              type="button"
              onClick={handleDeleteAll}
              style={{
                fontSize: "0.7rem", padding: "1px 7px",
                background: "var(--bs-danger)", color: "#fff",
                border: "none", borderRadius: 4, cursor: "pointer",
              }}
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => setConfirmDeleteAll(false)}
              style={{
                fontSize: "0.7rem", padding: "1px 7px",
                background: "rgba(255,255,255,0.08)", color: "var(--theme-text)",
                border: "none", borderRadius: 4, cursor: "pointer",
              }}
            >
              No
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmDeleteAll(true)}
            disabled={conversations.length === 0}
            style={{
              display: "flex", alignItems: "center", gap: 4,
              fontSize: "0.72rem", padding: "2px 8px",
              background: "transparent",
              color: conversations.length === 0 ? "rgba(255,255,255,0.2)" : "var(--bs-danger)",
              border: `1px solid ${conversations.length === 0 ? "rgba(255,255,255,0.1)" : "rgba(220,53,69,0.4)"}`,
              borderRadius: 4, cursor: conversations.length === 0 ? "default" : "pointer",
            }}
          >
            <LucideIcon name="trash-2" size={11} />
            Delete All
          </button>
        )}
      </div>

      {/* Scrollable list */}
      <div className="scroll-panel">
        {loading ? (
          <div className="p-3 text-center">
            <Spinner animation="border" size="sm" />
          </div>
        ) : conversations.length === 0 ? (
          <p className="text-muted small p-2">
            No conversations yet. Start a chat to create one.
          </p>
        ) : (
          conversations.map((c) => (
            <div
              key={c.id}
              onClick={() => onSelectConversation(c.id)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "6px 10px",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                cursor: "pointer",
                background: c.current ? "rgba(13,110,253,0.10)" : "transparent",
                borderLeft: c.current ? "2px solid var(--bs-primary)" : "2px solid transparent",
              }}
              onMouseEnter={(e) => {
                if (!c.current)
                  (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.05)";
              }}
              onMouseLeave={(e) => {
                if (!c.current)
                  (e.currentTarget as HTMLDivElement).style.background = "transparent";
              }}
            >
              <span
                style={{
                  fontSize: "0.78rem",
                  color: c.current ? "var(--bs-primary)" : "var(--theme-text)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  flex: 1,
                  minWidth: 0,
                }}
              >
                {c.title || `Chat #${c.id}`}
              </span>
              <button
                type="button"
                title="Delete conversation"
                onClick={(e) => {
                  e.stopPropagation();
                  remove(c.id);
                }}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "center",
                  width: 22, height: 22, padding: 0, flexShrink: 0, marginLeft: 6,
                  background: "transparent", border: "none", borderRadius: 4,
                  color: "rgba(255,255,255,0.3)", cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = "var(--bs-danger)";
                  (e.currentTarget as HTMLButtonElement).style.background = "rgba(220,53,69,0.12)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.3)";
                  (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                }}
              >
                <LucideIcon name="trash-2" size={12} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
