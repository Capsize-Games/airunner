import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import ListGroup from "react-bootstrap/ListGroup";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  listConversations,
  createConversation,
  deleteConversation,
} from "../../api/client";
import type { Conversation } from "../../types/api";

export default function Sidebar() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await listConversations();
      setConversations(data.conversations ?? []);
    } catch {
      // daemon not available yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleNew = async () => {
    try {
      const { id: _id } = await createConversation();
      await refresh();
      navigate("/chat");
    } catch {
      // ignore
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteConversation(id);
      await refresh();
    } catch {
      // ignore
    }
  };

  return (
    <aside className="sidebar p-2 d-flex flex-column">
      <Button
        variant="outline-primary"
        size="sm"
        className="mb-2"
        onClick={handleNew}
      >
        + New Chat
      </Button>
      {loading ? (
        <Spinner animation="border" size="sm" className="m-auto" />
      ) : (
        <ListGroup variant="flush" className="flex-grow-1 overflow-auto">
          {conversations.map((c) => (
            <ListGroup.Item
              key={c.id}
              action
              active={c.current}
              className="d-flex justify-content-between align-items-center"
              onClick={() => navigate("/chat")}
            >
              <span className="text-truncate">{c.title || `Chat #${c.id}`}</span>
              <Button
                variant="link"
                size="sm"
                className="text-danger p-0 ms-1"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(c.id);
                }}
              >
                ✕
              </Button>
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
    </aside>
  );
}
