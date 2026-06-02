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
  getSingleton,
} from "../../api/client";
import type { Message } from "../../types/api";
import MessageList from "./MessageList";

const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

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

  useEffect(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r) => {
        modelPathRef.current = String(r.model_path ?? "");
      })
      .catch(() => {});
  }, []);

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
      const gen = streamLLM(
        newMessages,
        controller.signal,
        modelPathRef.current,
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
  }, [input, messages, streaming]);

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
    <div className="d-flex flex-column h-100">
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
              color: "#c8c8c8",
              borderColor: "#333",
            }}
          />
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
