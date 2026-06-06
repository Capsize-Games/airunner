import { useState, useEffect, useCallback } from "react";
import {
  listConversations,
  deleteConversation,
} from "../../api/client";
import type {
  Conversation,
} from "../../types/api";
import Spinner from "react-bootstrap/Spinner";
import ListGroup from "react-bootstrap/ListGroup";

// ── Chat History ──
export function ChatHistoryPanel({
  onSelectConversation,
}: {
  onSelectConversation: (id: number) => void;
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await listConversations(50);
      setConversations(data.conversations ?? []);
    } catch {
      // daemon not available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleDelete = async (id: number) => {
    try {
      await deleteConversation(id);
      await refresh();
    } catch {
      // ignore
    }
  };

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">Chat History</h6>
        <button
          type="button"
          className="btn btn-sm btn-outline-danger"
          onClick={() =>
            conversations.forEach((c) => handleDelete(c.id))
          }
        >
          Clear All
        </button>
      </div>

      {loading ? (
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      ) : conversations.length === 0 ? (
        <p className="text-muted small">
          No conversations yet. Start a chat to create one.
        </p>
      ) : (
        <ListGroup variant="flush">
          {conversations.map((c) => (
            <ListGroup.Item
              key={c.id}
              action
              active={c.current}
              className="d-flex justify-content-between align-items-center py-1 px-2 bg-transparent"
              onClick={() => onSelectConversation(c.id)}
            >
              <small className="text-truncate">
                {c.title || `Chat #${c.id}`}
              </small>
              <span
                role="button"
                tabIndex={0}
                className="text-danger p-0 ms-1"
                style={{ cursor: "pointer", fontSize: "0.875rem", lineHeight: 1 }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(c.id);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.stopPropagation();
                    handleDelete(c.id);
                  }
                }}
                title="Delete"
              >
                ✕
              </span>
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
    </div>
  );
}
