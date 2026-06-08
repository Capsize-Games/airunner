import {
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import Alert from "react-bootstrap/Alert";
import ProgressBar from "react-bootstrap/ProgressBar";
import { getSingleton } from "../../api/client";
import MessageList from "./MessageList";
import ModelSelector from "./ModelSelector";
import ActiveDocPills from "./ActiveDocPills";
import LucideIcon from "../shared/LucideIcon";
import { useLLMWebSocket } from "../../features/llm/useLLMWebSocket";
import { useConversationMessages } from "../../hooks/useConversationMessages";
import { useKnowledgeBaseDocs } from "../../hooks/useKnowledgeBaseDocs";
import { useLocalStorage } from "../../hooks/useLocalStorage";
import { KnowledgeBasePanel } from "../panels/KnowledgeBasePanel";
import { ChatHistoryPanel } from "../panels/ChatHistoryPanel";
import { LLMSettingsPanel } from "../panels/LLMSettingsPanel";

type ChatTab = "chat" | "knowledge" | "history" | "llm_settings";

const TABS: { id: ChatTab; label: string; icon: string }[] = [
  { id: "chat", label: "Chat", icon: "bot-message-square" },
  { id: "knowledge", label: "Knowledge Base", icon: "book" },
  { id: "history", label: "History", icon: "history" },
  { id: "llm_settings", label: "LLM Settings", icon: "sliders-horizontal" },
];

interface ActiveDoc {
  id: number;
  name: string;
}

export default function ChatView({
  conversationId,
  onSelectConversation,
}: {
  conversationId: number | null;
  onSelectConversation?: (id: number) => void;
}) {
  const [tab, setTab] = useState<ChatTab>("chat");
  const [textareaH, setTextareaH] = useState(() => {
    try { return Number(localStorage.getItem("chat_textarea_h")) || 200; }
    catch { return 220; }
  });
  const textareaDrag = useRef(false);
  const textareaStartY = useRef(0);
  const textareaStartH = useRef(0);

  const handleTextareaResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    textareaDrag.current = true;
    textareaStartY.current = e.clientY;
    textareaStartH.current = textareaH;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";

    const onMove = (ev: MouseEvent) => {
      if (!textareaDrag.current) return;
      const delta = ev.clientY - textareaStartY.current;
      const newH = Math.max(200, Math.min(500, textareaStartH.current - delta));
      setTextareaH(newH);
    };

    const onUp = () => {
      textareaDrag.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [textareaH]);
  const { messages, loading, setMessages, load, appendMessage, deleteMessagesAfter } =
    useConversationMessages();
  const { docs: kbDocs, reload: reloadDocs } = useKnowledgeBaseDocs();
  const [, setStoredConvId] = useLocalStorage<number | null>(
    "airunner_conversation_id",
    null,
  );

  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const llm = useLLMWebSocket();
  const modelPathRef = useRef("");
  const loadedConvRef = useRef<number | null>(null);
  const conversationIdRef = useRef<number | null>(conversationId);

  useEffect(() => {
    if (conversationId !== null) {
      conversationIdRef.current = conversationId;
    }
  }, [conversationId]);

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

  useEffect(() => {
    if (!conversationId) return;
    if (loadedConvRef.current === conversationId) return;
    loadedConvRef.current = conversationId;
    load(conversationId);
  }, [conversationId, load]);

  // ── Core send helper ──────────────────────────────────────────────
  // Sends a list of messages (already in state) through the WS and
  // appends the assistant reply.  The caller is responsible for having
  // updated state *before* calling this.
  const doInference = useCallback(
    async (msgs: import("../../types/api").Message[]) => {
      if (!modelPathRef.current) {
        setError("Please select an LLM model in Settings first.");
        return;
      }
      setError(null);

      const activeDocIds = activeDocs.map((d) => d.id);

      try {
        const chunks = await llm.send(msgs as import("../../types/api").Message[], {
          model: modelPathRef.current,
          conversation_id: conversationIdRef.current ?? undefined,
          active_document_ids:
            activeDocIds.length > 0 ? activeDocIds : undefined,
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

        const nextIndex = msgs.length;

        // Always show the streamed content (may include tool call XML).
        if (fullResponse) {
          const assistantMsg = {
            role: "assistant" as const,
            content: fullResponse,
            thinking_content: thinking || undefined,
          };
          await appendMessage(
            conversationIdRef.current ?? 0,
            assistantMsg,
            nextIndex,
          );
        }

        // Conversation ID is tracked via conversationIdRef; no need to
        // refetch all messages here — appendMessage already persisted the
        // response and a full reload would risk duplicates.
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Stream failed";
        setError(msg);
      }
    },
    [activeDocs, llm, appendMessage, setStoredConvId],
  );

  // ── Send (new message) ────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || llm.streaming) return;
    if (!modelPathRef.current) {
      setError("Please select an LLM model in Settings first.");
      return;
    }
    setInput("");

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    const newMessages: import("../../types/api").Message[] = [
      ...messages,
      { role: "user" as const, content: text },
    ];

    await doInference(newMessages);
  }, [input, messages, llm.streaming, setMessages, doInference]);

  // ── Delete message (and all after it) ─────────────────────────────
  const handleDeleteMessage = useCallback(
    async (index: number) => {
      const convId = conversationIdRef.current;
      if (convId !== null) {
        try {
          const { truncateConversation } = await import("../../api/chat");
          await truncateConversation(convId, index);
        } catch {
          setError("Failed to delete message on server. Local state not changed.");
          return;
        }
        deleteMessagesAfter(convId, index);
      } else {
        setMessages((prev) => prev.slice(0, index));
      }
    },
    [setMessages, deleteMessagesAfter],
  );

  // ── Edit message (truncate chain + re-infer) ──────────────────────
  const handleSubmitEdit = useCallback(
    async (index: number, newContent: string) => {
      const convId = conversationIdRef.current;
      if (convId !== null) {
        try {
          const { truncateConversation } = await import("../../api/chat");
          await truncateConversation(convId, index);
        } catch {
          setError("Failed to truncate conversation on server. Edit aborted.");
          return;
        }
      }
      const truncated = messages.slice(0, index);
      const edited: import("../../types/api").Message[] = [
        ...truncated,
        { role: "user" as const, content: newContent },
      ];
      setMessages(edited);
      await doInference(edited);
    },
    [messages, setMessages, doInference],
  );

  // ── Copy message to clipboard ─────────────────────────────────────
  const handleCopyMessage = useCallback((content: string) => {
    navigator.clipboard.writeText(content).catch(() => {
      // clipboard write failed — silently ignore
    });
  }, []);

  // ── Play TTS ──────────────────────────────────────────────────────
  const handlePlayMessage = useCallback(async (content: string) => {
    try {
      const { synthesizeTTS } = await import("../../api/chat");
      const blob = await synthesizeTTS(content);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      // TTS failed — silently ignore
    }
  }, []);

  // ── Cancel ────────────────────────────────────────────────────────
  const handleCancel = useCallback(() => llm.cancel(), [llm]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = useCallback(async () => {
    try {
      const { createConversation } = await import("../../api/client");
      const result = await createConversation();
      const newId = result.id;
      conversationIdRef.current = newId;
      setStoredConvId(newId);
      setMessages([]);
      loadedConvRef.current = newId;
    } catch {
      // If server call fails, at least clear local state
      setMessages([]);
      setStoredConvId(null);
    }
  }, [setMessages, setStoredConvId]);

  useEffect(() => {
    try { localStorage.setItem("chat_textarea_h", String(textareaH)); } catch { /* */ }
  }, [textareaH]);

  return (
    <div
      className="d-flex flex-column h-100"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Tab bar — icons only with tooltips */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            title={t.label}
            style={{
              flex: 1,
              padding: "6px 0",
              background: tab === t.id
                ? "var(--theme-panel-bg)"
                : "transparent",
              border: "none",
              borderBottom: tab === t.id
                ? "2px solid var(--bs-primary)"
                : "2px solid transparent",
              color: tab === t.id
                ? "var(--bs-primary)"
                : "rgba(255,255,255,0.45)",
              fontSize: 11,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "color 0.15s, border-color 0.15s",
            }}
          >
            <LucideIcon name={t.icon} size={16} />
          </button>
        ))}
        <button
          type="button"
          onClick={handleNewConversation}
          title="New conversation"
          style={{
            padding: "0 8px",
            background: "transparent",
            border: "none",
            borderBottom: "2px solid transparent",
            color: "rgba(255,255,255,0.4)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            flexShrink: 0,
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.4)"; }}
        >
          <LucideIcon name="plus" size={15} />
        </button>
      </div>

      {/* Tab content */}
      {tab === "chat" && (
        <>

          {error && (
            <Alert variant="danger" dismissible onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <div className="chat-messages p-2" style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
            {loading ? null : (
              <MessageList
                messages={messages}
            streamBuffer={llm.streamBuffer}
            thinkingBuffer={llm.thinkingBuffer}
            onDeleteMessage={handleDeleteMessage}
            onSubmitEdit={handleSubmitEdit}
            onCopyMessage={handleCopyMessage}
            onPlayMessage={handlePlayMessage}
              />
            )}
          </div>

          <div
            onMouseDown={handleTextareaResize}
            style={{
              height: 4,
              cursor: "row-resize",
              flexShrink: 0,
              background: "transparent",
              transition: "background 0.15s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.background =
                "rgba(99,153,255,0.3)";
            }}
            onMouseLeave={(e) => {
              if (!textareaDrag.current) {
                (e.currentTarget as HTMLDivElement).style.background =
                  "transparent";
              }
            }}
          />

          <div
            className="chat-input-area border-top p-2"
            style={{
              height: textareaH,
              flexShrink: 0,
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <ActiveDocPills activeDocs={activeDocs} onRemoveDoc={handleRemoveDoc} />

            <textarea
              style={{
                resize: "none",
                flex: 1,
                background: "#1a1a2e",
                color: "var(--theme-text)",
                borderColor: "#333",
                minHeight: 60,
              }}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              disabled={llm.streaming}
              className="form-control"
            />

            <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              <ModelSelector />
              {llm.activeTools.length > 0 && (
                <div
                  className="px-2 pb-1"
                  style={{ fontSize: "0.75rem", color: "var(--bs-info)" }}
                >
                  {llm.activeTools.map((t) => (
                    <div key={t.tool_id} className="d-flex align-items-center gap-1">
                      <span>⚙</span>
                      <span>{t.tool_name} running…</span>
                    </div>
                  ))}
                </div>
              )}
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
                      minWidth: 30,
                      height: 30,
                      border: "none",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
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
                      minWidth: 30,
                      height: 30,
                      border: "none",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <LucideIcon name="chevron-up" size={16} />
                  </button>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {tab === "knowledge" && (
        <div className="flex-grow-1 overflow-auto">
          <KnowledgeBasePanel />
        </div>
      )}

      {tab === "history" && (
        <div className="flex-grow-1 overflow-auto">
          <ChatHistoryPanel
            onSelectConversation={(id) => {
              onSelectConversation?.(id);
              setTab("chat");
            }}
          />
        </div>
      )}

      {tab === "llm_settings" && (
        <div className="flex-grow-1 overflow-auto">
          <LLMSettingsPanel />
        </div>
      )}
    </div>
  );
}
