import {
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import Alert from "react-bootstrap/Alert";
import ProgressBar from "react-bootstrap/ProgressBar";
import {
  streamLLM,
  listKnowledgeBaseDocuments,
  getSingleton,
} from "../../api/client";
import type { Message } from "../../types/api";
import MessageList from "./MessageList";
import ModelSelector from "./ModelSelector";

const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

interface ActiveDoc {
  id: number;
  name: string;
}

export default function ChatView({
  conversationId,
}: {
  conversationId: number | null;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [thinkingBuffer, setThinkingBuffer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const modelPathRef = useRef("");
  const loadedConvRef = useRef<number | null>(null);

  // ── Active RAG documents state ──
  const [activeDocs, setActiveDocs] = useState<ActiveDoc[]>([]);

  const reloadActiveDocs = useCallback(async () => {
    try {
      const data = await listKnowledgeBaseDocuments();
      const docs = (data.documents ?? [])
        .filter((d) => d.active)
        .map((d) => ({
          id: d.id,
          name: d.path.split("/").pop() || d.path,
        }));
      setActiveDocs(docs);
    } catch {
      // unavailable
    }
  }, []);

  useEffect(() => {
    reloadActiveDocs();
  }, [reloadActiveDocs]);

  // Listen for knowledge-base changes from other panels
  useEffect(() => {
    const handler = () => reloadActiveDocs();
    window.addEventListener("knowledge-base-changed", handler);
    return () =>
      window.removeEventListener("knowledge-base-changed", handler);
  }, [reloadActiveDocs]);

  // ── Drag-and-drop: accept doc IDs onto the chat ──
  const handleDragOver = (e: React.DragEvent) => {
    if (e.dataTransfer.types.includes("application/x-airunner-doc-id")) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    const raw = e.dataTransfer.getData("application/x-airunner-doc-id");
    if (!raw) return;
    const docId = Number(raw);
    if (Number.isNaN(docId)) return;

    // Toggle the document active
    try {
      const { toggleDocumentActive } = await import("../../api/client");
      await toggleDocumentActive(docId);
      await reloadActiveDocs();
      window.dispatchEvent(new Event("knowledge-base-changed"));
    } catch {
      // unchanged
    }
  };

  // ── Remove an active document pill ──
  const handleRemoveDoc = async (docId: number) => {
    try {
      const { toggleDocumentActive } = await import("../../api/client");
      await toggleDocumentActive(docId);
      await reloadActiveDocs();
      window.dispatchEvent(new Event("knowledge-base-changed"));
    } catch {
      // unchanged
    }
  };

  const loadModelPath = useCallback(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r) => {
        modelPathRef.current = String(r.model_path ?? "");
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadModelPath();
    const handler = () => loadModelPath();
    window.addEventListener("model-settings-changed", handler);
    return () =>
      window.removeEventListener("model-settings-changed", handler);
  }, [loadModelPath]);

  // Load conversation when conversationId changes
  useEffect(() => {
    if (!conversationId) return;
    if (loadedConvRef.current === conversationId) return;
    loadedConvRef.current = conversationId;
    import("../../api/client").then(
      ({ loadConversation, selectConversation }) => {
        selectConversation(conversationId)
          .then((session) => {
            const msgs = (session.messages ?? []).map(
              (raw: Record<string, unknown>) => {
                // Strip "assistant " prefix that the legacy
                // system prepends to assistant message content.
                let content = String(raw.content ?? "");
                if (
                  raw.is_bot &&
                  content.toLowerCase().startsWith("assistant ")
                ) {
                  content = content.slice(10);
                }
                return {
                  role: raw.is_bot ? "assistant" : "user",
                  content,
                  thinking_content: raw.thinking_content
                    ? String(raw.thinking_content)
                    : undefined,
                };
              },
            );
            setMessages(msgs as Message[]);
          })
          .catch(() => {});
      },
    );
  }, [conversationId]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;
    if (!modelPathRef.current) {
      setError("Please select an LLM model in Settings first.");
      return;
    }
    setError(null);
    setInput("");
    setThinkingBuffer("");

    const userMsg: Message = { role: "user", content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setStreaming(true);
    setStreamBuffer("");

    const controller = new AbortController();
    abortRef.current = controller;

    let fullResponse = "";
    try {
      let llmOverrides: Record<string, Record<string, unknown>> | undefined;
      try {
        const ui = localStorage.getItem("airunner_llm_overrides_ui");
        if (ui && (JSON.parse(ui) as Record<string, unknown>).overrideEnabled) {
          const raw = localStorage.getItem("airunner_llm_overrides");
          if (raw) llmOverrides = JSON.parse(raw) as Record<string, Record<string, unknown>>;
        }
      } catch { /* ignore */ }

      const activeIds = activeDocs.map((d) => d.id);

      const gen = streamLLM(
        newMessages,
        controller.signal,
        modelPathRef.current,
        llmOverrides,
        activeIds.length > 0 ? activeIds : undefined,
      );
      fullResponse = "";
      let thinking = "";
      for await (const chunk of gen) {
        if (chunk.error) {
          setError(chunk.error);
          break;
        }
        if (chunk.message_type === "thinking") {
          thinking = chunk.token ?? "";
          setThinkingBuffer(thinking);
        } else if (chunk.token) {
          fullResponse += chunk.token;
          setStreamBuffer(fullResponse);
        }
      }
      if (fullResponse && !controller.signal.aborted) {
        setMessages([
          ...newMessages,
          {
            role: "assistant",
            content: fullResponse,
            thinking_content: thinking || undefined,
          },
        ]);
        // Persist the newest conversation so reloads restore it
        import("../../api/client").then(
          ({ listConversations }) => {
            listConversations(1)
              .then((resp) => {
                const convs = resp.conversations ?? [];
                if (convs.length > 0) {
                  const id = convs[0].id;
                  try {
                    localStorage.setItem(
                      "airunner_conversation_id",
                      String(id),
                    );
                  } catch {}
                }
              })
              .catch(() => {});
          },
        );
      }
    } catch (err: unknown) {
      if (!controller.signal.aborted) {
        const msg =
          err instanceof Error ? err.message : "Stream failed";
        setError(msg);
      }
    } finally {
      setStreamBuffer("");
      setThinkingBuffer("");
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, messages, streaming, activeDocs]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
    setStreamBuffer("");
    setThinkingBuffer("");
  }, []);

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = useCallback(() => {
    setMessages([]);
    try {
      localStorage.removeItem("airunner_conversation_id");
    } catch {}
  }, []);

  return (
    <div
      className="d-flex flex-column h-100"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* New conversation button — top right */}
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
          }}
        >
          <img
            src={icon("plus")}
            alt="New"
            style={{ width: 14, height: 14, filter: "invert(0.7)" }}
          />
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <Alert
          variant="danger"
          dismissible
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      {/* Messages */}
      <div className="chat-messages p-2 flex-grow-1">
        <MessageList
          messages={messages}
          streamBuffer={streamBuffer}
          thinkingBuffer={thinkingBuffer}
        />
      </div>

      {/* Input area */}
      <div className="chat-input-area border-top p-2">
        <div className="d-flex flex-column gap-2">
          {/* Active document pills */}
          {activeDocs.length > 0 && (
            <div className="d-flex flex-wrap gap-1">
              {activeDocs.map((doc) => (
                <span
                  key={doc.id}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    background: "rgba(0,132,185,0.2)",
                    border: "1px solid var(--bs-primary)",
                    borderRadius: 12,
                    padding: "2px 8px",
                    fontSize: "0.7rem",
                    color: "var(--theme-text)",
                  }}
                >
                  <span
                    style={{
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      lineHeight: 1,
                      color: "#ff5555",
                      fontSize: "0.8rem",
                    }}
                    onClick={() => handleRemoveDoc(doc.id)}
                    title="Remove from RAG"
                  >
                    ✕
                  </span>
                  {doc.name}
                </span>
              ))}
            </div>
          )}

          <textarea
            rows={3}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
            disabled={streaming}
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
                now={streamBuffer ? 50 : 0}
                variant={streaming ? "info" : "secondary"}
                style={{ height: 6 }}
                animated={streaming}
              />
            </div>
            {streaming ? (
              <button
                className="btn btn-sm btn-danger p-1"
                onClick={handleCancel}
                title="Cancel"
                style={{
                  minWidth: 30,
                  height: 30,
                  border: "none",
                }}
              >
                <img
                  src={icon("circle-x")}
                  alt="Cancel"
                  style={{
                    width: 16,
                    height: 16,
                    filter: "invert(1)",
                  }}
                />
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
                  minWidth: 30,
                  height: 30,
                  border: "none",
                }}
              >
                <img
                  src={icon("chevron-up")}
                  alt="Send"
                  style={{
                    width: 16,
                    height: 16,
                    filter: "invert(1)",
                  }}
                />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
