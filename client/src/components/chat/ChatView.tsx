import {
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import Alert from "react-bootstrap/Alert";
import { getSingleton, listActiveModels } from "../../api/client";
import type { ActiveModelInfo } from "../../api/client";
import MessageList from "./MessageList";
import ModelSelector from "./ModelSelector";
import LucideIcon from "../shared/LucideIcon";
import { useLLMWebSocket } from "../../features/llm/useLLMWebSocket";
import { useConversationMessages } from "../../hooks/useConversationMessages";
import { useKnowledgeBaseDocs } from "../../hooks/useKnowledgeBaseDocs";
import { useLocalStorage } from "../../hooks/useLocalStorage";
import { KnowledgeBasePanel } from "../panels/KnowledgeBasePanel";
import { ChatHistoryPanel } from "../panels/ChatHistoryPanel";

type ChatPanel = "knowledge" | "history" | null;

interface ActiveDoc {
  id: number;
  name: string;
}


export default function ChatView({
  conversationId,
  onSelectConversation,
  ttsOn = false,
  sttOn = false,
  onToggleTts,
  onToggleStt,
}: {
  conversationId: number | null;
  onSelectConversation?: (id: number) => void;
  ttsOn?: boolean;
  sttOn?: boolean;
  onToggleTts?: () => void;
  onToggleStt?: () => void;
}) {
  const [openPanel, setOpenPanel] = useState<ChatPanel>(null);
  const [popupAnchor, setPopupAnchor] = useState<{ left: number; bottom: number; width: number; height: number } | null>(null);
  const inputAreaRef = useRef<HTMLDivElement>(null);

  const [modelStatus, setModelStatus] = useState<string>("unloaded");

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await listActiveModels();
        const llm = resp.models.find(
          (m: ActiveModelInfo) => m.model_type.toLowerCase() === "llm",
        );
        setModelStatus(llm?.status ?? "unloaded");
      } catch {
        // endpoint may be unavailable
      }
    };
    fetch();
    const id = setInterval(fetch, 300);
    return () => clearInterval(id);
  }, []);

  // Compute fixed anchor and close-on-outside-click when panel opens
  useEffect(() => {
    if (!openPanel) {
      setPopupAnchor(null);
      return;
    }
    if (inputAreaRef.current) {
      const rect = inputAreaRef.current.getBoundingClientRect();
      // bottom aligns the popup above the toolbar rows so it covers the textarea only
      const belowInputArea = window.innerHeight - rect.bottom + 66;
      setPopupAnchor({
        left: rect.left,
        bottom: belowInputArea,
        width: rect.width,
        height: Math.min(480, rect.bottom - 74),
      });
    }
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const insideInputArea = inputAreaRef.current?.contains(target);
      const insidePopup = document.getElementById("chat-panel-popup")?.contains(target);
      if (!insideInputArea && !insidePopup) setOpenPanel(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [openPanel]);

  const isModelLoading = modelStatus === "loading";
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
        const thinking = thinkingChunks.join("").trim();

        const nextIndex = msgs.length;

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
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Stream failed";
        setError(msg);
      }
    },
    [activeDocs, llm, appendMessage],
  );

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || llm.streaming) return;
    if (!modelPathRef.current) {
      setError("Please select an LLM model in Settings first.");
      return;
    }
    setInput("");

    if (conversationIdRef.current === null) {
      try {
        const { createConversation } = await import("../../api/client");
        const result = await createConversation();
        conversationIdRef.current = result.conversation_id;
        setStoredConvId(result.conversation_id);
        loadedConvRef.current = result.conversation_id;
      } catch {
        // Proceed without a conversation ID; history won't survive a reload.
      }
    }

    const userMsgIndex = messages.length;
    const userMsg: import("../../types/api").Message = {
      role: "user" as const,
      content: text,
    };
    if (conversationIdRef.current !== null) {
      await appendMessage(
        conversationIdRef.current,
        userMsg,
        userMsgIndex,
      );
    } else {
      setMessages((prev) => [...prev, userMsg]);
    }
    const newMessages: import("../../types/api").Message[] = [
      ...messages,
      userMsg,
    ];

    await doInference(newMessages);
  }, [input, messages, llm.streaming, setMessages, appendMessage, setStoredConvId, doInference]);

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

  const handleCopyMessage = useCallback((content: string) => {
    navigator.clipboard.writeText(content).catch(() => {});
  }, []);

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
      const newId = result.conversation_id;
      conversationIdRef.current = newId;
      setStoredConvId(newId);
      setMessages([]);
      loadedConvRef.current = newId;
    } catch {
      setMessages([]);
      setStoredConvId(null);
    }
  }, [setMessages, setStoredConvId]);

  useEffect(() => {
    try { localStorage.setItem("chat_textarea_h", String(textareaH)); } catch { /* */ }
  }, [textareaH]);

  useEffect(() => {
    const handler = () => setOpenPanel(null);
    window.addEventListener("chat-picker-opened", handler);
    return () => window.removeEventListener("chat-picker-opened", handler);
  }, []);

  const togglePanel = (panel: NonNullable<ChatPanel>) =>
    setOpenPanel((prev) => (prev === panel ? null : panel));

  const docCount = activeDocs.length;

  return (
    <div
      className="d-flex flex-column h-100"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <div className="chat-messages p-2" style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
        {loading ? null : (
          <>
            <MessageList
              messages={messages}
              streamBuffer={llm.streamBuffer}
              thinkingBuffer={llm.thinkingBuffer}
              onDeleteMessage={handleDeleteMessage}
              onSubmitEdit={handleSubmitEdit}
              onCopyMessage={handleCopyMessage}
              onPlayMessage={handlePlayMessage}
            />
            {isModelLoading && messages.length > 0 && (
              <div
                className="p-2 rounded w-100 mt-2"
                style={{
                  background: "rgba(255,193,7,0.10)",
                  border: "1px solid rgba(255,193,7,0.20)",
                }}
              >
                <div className="d-flex align-items-center gap-2">
                  <LucideIcon name="loader" size={16} />
                  <small style={{ color: "var(--theme-text-secondary)" }}>
                    Loading model…
                  </small>
                </div>
              </div>
            )}
          </>
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
          (e.currentTarget as HTMLDivElement).style.background = "rgba(99,153,255,0.3)";
        }}
        onMouseLeave={(e) => {
          if (!textareaDrag.current) {
            (e.currentTarget as HTMLDivElement).style.background = "transparent";
          }
        }}
      />

      <div
        ref={inputAreaRef}
        className="chat-input-area"
        style={{
          height: textareaH,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Connected textarea + toolbar container */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            border: "none",
            borderRadius: 0,
            background: "#1a1a2e",
            minHeight: 0,
          }}
        >
          <textarea
            style={{
              resize: "none",
              flex: 1,
              background: "transparent",
              color: "var(--theme-text)",
              border: "none",
              outline: "none",
              padding: "8px 10px",
              minHeight: 0,
              fontFamily: "inherit",
              fontSize: "inherit",
            }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={llm.streaming}
          />

          {llm.activeTools.length > 0 && (
            <div
              style={{
                padding: "2px 10px",
                fontSize: "0.72rem",
                color: "var(--bs-info)",
                borderTop: "1px solid rgba(255,255,255,0.06)",
                background: "rgba(13,202,240,0.04)",
              }}
            >
              {llm.activeTools.map((t) => (
                <div key={t.tool_id} className="d-flex align-items-center gap-1">
                  <span>⚙</span>
                  <span>{t.tool_name} running…</span>
                </div>
              ))}
            </div>
          )}

          {/* Docs row — above the model/toolbar row */}
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
            {/* Left: doc icon + count → knowledge popup */}
            <button
              type="button"
              onClick={() => togglePanel("knowledge")}
              title="Knowledge base"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                background: openPanel === "knowledge" ? "rgba(255,255,255,0.08)" : "transparent",
                border: "none",
                cursor: "pointer",
                padding: "2px 5px",
                borderRadius: 4,
                color: openPanel === "knowledge" ? "var(--bs-primary)" : "rgba(255,255,255,0.4)",
                fontSize: "0.72rem",
              }}
              onMouseEnter={(e) => {
                if (openPanel !== "knowledge")
                  (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)";
              }}
              onMouseLeave={(e) => {
                if (openPanel !== "knowledge")
                  (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              }}
            >
              <LucideIcon name="book" size={12} />
              <span>{docCount} Active document{docCount !== 1 ? "s" : ""}</span>
            </button>

            <span style={{ flex: 1 }} />

            {/* Right: history icon */}
            <PanelIconBtn
              icon="history"
              title="Chat history"
              active={openPanel === "history"}
              onClick={() => togglePanel("history")}
            />
          </div>

          {/* Toolbar row */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              padding: "3px 4px",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              flexShrink: 0,
            }}
          >
            {/* New chat button */}
            <button
              type="button"
              onClick={handleNewConversation}
              title="New conversation"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 26,
                height: 26,
                padding: 0,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                borderRadius: 4,
                color: "rgba(255,255,255,0.45)",
                flexShrink: 0,
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)";
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.45)";
                (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              }}
            >
              <LucideIcon name="plus" size={15} />
            </button>

            <span
              style={{
                width: 1,
                height: 14,
                background: "rgba(255,255,255,0.12)",
                flexShrink: 0,
              }}
            />

            <ModelSelector />

            <ToolbarToggle
              active={ttsOn}
              title="Text to Speech"
              onClick={onToggleTts}
              icon="speaker"
            />

            <ToolbarToggle
              active={sttOn}
              title="Speech to Text"
              onClick={onToggleStt}
              icon="mic"
            />

            {llm.streaming ? (
              <button
                type="button"
                onClick={handleCancel}
                title="Cancel"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 28,
                  height: 28,
                  padding: 0,
                  background: "var(--bs-danger)",
                  border: "none",
                  cursor: "pointer",
                  borderRadius: 5,
                  flexShrink: 0,
                }}
              >
                <LucideIcon name="circle-x" size={15} />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!input.trim()}
                title="Send message"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 28,
                  height: 28,
                  padding: 0,
                  background: input.trim() ? "var(--bs-primary)" : "rgba(255,255,255,0.1)",
                  border: "none",
                  cursor: input.trim() ? "pointer" : "default",
                  borderRadius: 5,
                  flexShrink: 0,
                }}
              >
                <LucideIcon name="chevron-up" size={15} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Fixed popup — sits above input area, can overlap the art panel */}
      {openPanel && popupAnchor && (
        <div
          id="chat-panel-popup"
          style={{
            position: "fixed",
            left: popupAnchor.left,
            bottom: popupAnchor.bottom,
            // Expand past the chat panel boundary when compact
            width: Math.max(popupAnchor.width, 360),
            // Fixed height so height:100% resolves correctly in child flex layouts
            height: popupAnchor.height,
            zIndex: 1300,
            background: "var(--theme-panel-bg)",
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 0,
            boxShadow: "4px -4px 24px rgba(0,0,0,0.7)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {openPanel === "knowledge" && <KnowledgeBasePanel />}
          {openPanel === "history" && (
            <ChatHistoryPanel
              onSelectConversation={(id) => {
                onSelectConversation?.(id);
                setOpenPanel(null);
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}

function PanelIconBtn({
  icon,
  title,
  active,
  onClick,
}: {
  icon: string;
  title: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 24,
        height: 24,
        padding: 0,
        background: active ? "rgba(255,255,255,0.08)" : "transparent",
        border: "none",
        cursor: "pointer",
        borderRadius: 4,
        color: active ? "var(--bs-primary)" : "rgba(255,255,255,0.4)",
        flexShrink: 0,
        transition: "color 0.1s, background 0.1s",
      }}
      onMouseEnter={(e) => {
        if (!active) (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)";
      }}
      onMouseLeave={(e) => {
        if (!active) (e.currentTarget as HTMLButtonElement).style.background = "transparent";
      }}
    >
      <LucideIcon name={icon} size={13} />
    </button>
  );
}

function ToolbarToggle({
  active,
  title,
  onClick,
  icon,
}: {
  active: boolean;
  title: string;
  onClick?: () => void;
  icon: string;
}) {
  const [hovered, setHovered] = useState(false);

  let bg = "transparent";
  if (active && hovered) bg = "rgba(13,110,253,0.3)";
  else if (active) bg = "rgba(13,110,253,0.18)";
  else if (hovered) bg = "rgba(255,255,255,0.08)";

  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 26,
        height: 26,
        padding: 0,
        background: bg,
        border: active ? "1px solid rgba(13,110,253,0.4)" : "1px solid transparent",
        cursor: "pointer",
        borderRadius: 4,
        color: active ? "var(--bs-primary)" : "rgba(255,255,255,0.4)",
        flexShrink: 0,
        transition: "background 0.1s, border-color 0.1s",
      }}
    >
      <LucideIcon name={icon} size={15} />
    </button>
  );
}
