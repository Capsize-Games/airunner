import {
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import Alert from "react-bootstrap/Alert";
import ProgressBar from "react-bootstrap/ProgressBar";
import { getSingleton } from "../../api/client";
import type { StreamChunk } from "../../types/api";
import MessageList from "./MessageList";
import ModelSelector from "./ModelSelector";
import ActiveDocPills from "./ActiveDocPills";
import LucideIcon from "../shared/LucideIcon";
import { useLLMWebSocket } from "../../features/llm/useLLMWebSocket";
import { useConversationMessages } from "../../hooks/useConversationMessages";
import { useKnowledgeBaseDocs } from "../../hooks/useKnowledgeBaseDocs";
import { useLocalStorage } from "../../hooks/useLocalStorage";

interface ActiveDoc {
  id: number;
  name: string;
}

export default function ChatView({
  conversationId,
}: {
  conversationId: number | null;
}) {
  const { messages, setMessages, load, appendMessage } = useConversationMessages();
  const { docs: kbDocs, reload: reloadDocs } = useKnowledgeBaseDocs();
  const [, setStoredConvId] = useLocalStorage<number | null>("airunner_conversation_id", null);

  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const llm = useLLMWebSocket();
  const modelPathRef = useRef("");
  const loadedConvRef = useRef<number | null>(null);
  const conversationIdRef = useRef<number | null>(conversationId);
  if (conversationId !== null) {
    conversationIdRef.current = conversationId;
  }

  const activeDocs: ActiveDoc[] = kbDocs
    .filter((d) => d.active)
    .map((d) => ({
      id: d.id,
      name: d.path.split("/").pop() || d.path,
    }));

  const handleRemoveDoc = useCallback(async (docId: number) => {
    try {
      const { toggleDocumentActive } = await import("../../api/client");
      await toggleDocumentActive(docId);
      await reloadDocs();
      window.dispatchEvent(new Event("knowledge-base-changed"));
    } catch {
      // unchanged
    }
  }, [reloadDocs]);

  const handleDragOver = (e: React.DragEvent) => {
    if (e.dataTransfer.types.includes("application/x-airunner-doc-id")) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    }
  };

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    const raw = e.dataTransfer.getData("application/x-airunner-doc-id");
    if (!raw) return;
    const docId = Number(raw);
    if (Number.isNaN(docId)) return;
    try {
      const { toggleDocumentActive } = await import("../../api/client");
      await toggleDocumentActive(docId);
      await reloadDocs();
      window.dispatchEvent(new Event("knowledge-base-changed"));
    } catch {
      // unchanged
    }
  }, [reloadDocs]);

  const loadModelPath = useCallback(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r) => { modelPathRef.current = String(r.model_path ?? ""); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadModelPath();
    const handler = () => loadModelPath();
    window.addEventListener("model-settings-changed", handler);
    return () => window.removeEventListener("model-settings-changed", handler);
  }, [loadModelPath]);

  useEffect(() => {
    if (!conversationId) return;
    if (loadedConvRef.current === conversationId) return;
    loadedConvRef.current = conversationId;
    load(conversationId);
  }, [conversationId, load]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || llm.streaming) return;
    if (!modelPathRef.current) {
      setError("Please select an LLM model in Settings first.");
      return;
    }
    setError(null);
    setInput("");

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    const newMessages = [...messages, { role: "user" as const, content: text }];
    const activeDocIds = activeDocs.map((d) => d.id);

    try {
      const chunks = await llm.send(newMessages, {
        model: modelPathRef.current,
        conversation_id: conversationIdRef.current ?? undefined,
        active_document_ids: activeDocIds.length > 0 ? activeDocIds : undefined,
      });

      let fullResponse = "";
      const thinkingChunks: string[] = [];
      for (const chunk of chunks) {
        if (chunk.message_type === "thinking") {
          const token = chunk.token ?? "";
          if (token) thinkingChunks.push(token);
        } else if (chunk.token) {
          fullResponse += chunk.token;
        }
      }
      const thinking = thinkingChunks.join("");

      if (fullResponse) {
        const assistantMsg = {
          role: "assistant" as const,
          content: fullResponse,
          thinking_content: thinking || undefined,
        };
        const nextIndex = newMessages.length;
        await appendMessage(
          conversationIdRef.current ?? 0,
          assistantMsg,
          nextIndex,
        );

        // Refresh conversation list to pick up server-assigned conversation ID.
        import("../../api/client").then(({ listConversations }) => {
          listConversations(1)
            .then((resp) => {
              const convs = resp.conversations ?? [];
              if (convs.length > 0) {
                const id = convs[0].id;
                conversationIdRef.current = id;
                setStoredConvId(id);
              }
            })
            .catch(() => {});
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Stream failed";
      setError(msg);
    }
  }, [input, messages, llm, appendMessage, setMessages, setStoredConvId]);

  const handleCancel = useCallback(() => llm.cancel(), [llm]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = useCallback(() => {
    setMessages([]);
    setStoredConvId(null);
  }, [setMessages, setStoredConvId]);

  return (
    <div
      className="d-flex flex-column h-100"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div
        className="d-flex justify-content-end p-1 flex-shrink-0"
        style={{ borderBottom: "1px solid #333" }}
      >
        <button
          onClick={handleNewConversation}
          title="New conversation"
          style={{
            background: "transparent",
            border: "1px solid #444",
            borderRadius: 4,
            padding: "2px 4px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
          }}
        >
          <LucideIcon name="plus" size={14} />
        </button>
      </div>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <div className="chat-messages p-2 flex-grow-1">
        <MessageList
          messages={messages}
          streamBuffer={llm.streamBuffer}
          thinkingBuffer={llm.thinkingBuffer}
        />
      </div>

      <div className="chat-input-area border-top p-2">
        <div className="d-flex flex-column gap-2">
          <ActiveDocPills activeDocs={activeDocs} onRemoveDoc={handleRemoveDoc} />

          <textarea
            rows={3}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={llm.streaming}
            className="form-control"
            style={{
              resize: "none",
              background: "#1a1a2e",
              color: "var(--theme-text)",
              borderColor: "#333",
            }}
          />
          <ModelSelector />
          <div className="d-flex align-items-center gap-2">
            <div className="flex-grow-1">
              <ProgressBar
                now={llm.streamBuffer ? 50 : 0}
                variant={llm.streaming ? "info" : "secondary"}
                style={{ height: 6 }}
                animated={llm.streaming}
              />
            </div>
            {llm.streaming ? (
              <button
                className="btn btn-sm btn-danger p-1"
                onClick={handleCancel}
                title="Cancel"
                style={{
                  minWidth: 30, height: 30, border: "none",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}
              >
                <LucideIcon name="circle-x" size={16} />
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-sm p-1"
                onClick={handleSend}
                disabled={!input.trim()}
                title="Send message"
                style={{
                  background: "var(--bs-primary)",
                  minWidth: 30, height: 30, border: "none",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}
              >
                <LucideIcon name="chevron-up" size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
