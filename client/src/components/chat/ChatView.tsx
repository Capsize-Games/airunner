import { useEffect, useRef, useMemo } from "react";
import Alert from "react-bootstrap/Alert";
import { useLLMWebSocket } from "../../features/llm/useLLMWebSocket";
import { useConversationMessages } from "../../hooks/useConversationMessages";
import { useKnowledgeBaseDocs } from "../../hooks/useKnowledgeBaseDocs";
import { useChatModelStatus } from "../../hooks/useChatModelStatus";
import { useChatPopupPanel } from "../../hooks/useChatPopupPanel";
import { useChatTextareaResize } from "../../hooks/useChatTextareaResize";
import { useChatModelPath } from "../../hooks/useChatModelPath";
import { useChatInference } from "../../hooks/useChatInference";
import { useChatMessageActions } from "../../hooks/useChatMessageActions";
import MessageList from "./MessageList";
import ModelLoadingIndicator from "./input/ModelLoadingIndicator";
import ChatInputArea from "./input/ChatInputArea";
import ChatPopupPanel from "./panels/ChatPopupPanel";

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
  // ── Hooks ──────────────────────────────────────────────────────────────────
  const { isModelLoading } = useChatModelStatus();
  const { openPanel, popupAnchor, setOpenPanel, togglePanel, inputAreaRef } =
    useChatPopupPanel();
  const { textareaH, textareaDrag, handleTextareaResize } =
    useChatTextareaResize();
  const { modelPathRef } = useChatModelPath();
  const { messages, loading, setMessages, load, cancelLoad, appendMessage, deleteMessagesAfter } =
    useConversationMessages();
  const { docs: kbDocs, reload: reloadDocs } = useKnowledgeBaseDocs();
  const llm = useLLMWebSocket();

  const conversationIdRef = useRef<number | null>(conversationId);
  const loadedConvRef = useRef<number | null>(null);

  useEffect(() => {
    if (conversationId !== null) {
      conversationIdRef.current = conversationId;
    }
  }, [conversationId]);

  // Load conversation when ID changes (skip if already loaded via new-conv flow)
  useEffect(() => {
    if (!conversationId) return;
    if (loadedConvRef.current === conversationId) return;
    loadedConvRef.current = conversationId;
    load(conversationId);
  }, [conversationId, load]);

  const activeDocs = useMemo(
    () =>
      kbDocs
        .filter((d) => d.active)
        .map((d) => ({ id: d.id, name: d.path.split("/").pop() || d.path })),
    [kbDocs],
  );

  // ── Inference ──────────────────────────────────────────────────────────────
  const {
    input,
    setInput,
    error,
    setError,
    doInference,
    handleSend,
    handleCancel,
    handleKeyDown,
    handleNewConversation,
  } = useChatInference({
    messages,
    setMessages,
    appendMessage,
    cancelLoad,
    onSelectConversation,
    conversationIdRef,
    loadedConvRef,
    modelPathRef,
    llm,
    activeDocs,
  });

  // ── Message Actions ────────────────────────────────────────────────────────
  const {
    handleDeleteMessage,
    handleSubmitEdit,
    handleCopyMessage,
    handlePlayMessage,
  } = useChatMessageActions({
    conversationIdRef,
    messages,
    setMessages,
    deleteMessagesAfter,
    setError,
    doInference,
  });

  // ── Drag-and-drop RAG docs ─────────────────────────────────────────────────
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
    try {
      const { toggleDocumentActive } = await import("../../api/client");
      await toggleDocumentActive(docId);
      await reloadDocs();
      window.dispatchEvent(new Event("knowledge-base-changed"));
    } catch {
      // unchanged
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
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

      <div
        className="chat-messages p-2"
        style={{ flex: 1, minHeight: 0, overflow: "auto" }}
      >
        {!loading && (
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
            <ModelLoadingIndicator
              visible={isModelLoading && messages.length > 0}
            />
          </>
        )}
      </div>

      <ChatInputArea
        input={input}
        setInput={setInput}
        handleKeyDown={handleKeyDown}
        handleTextareaResize={handleTextareaResize}
        textareaDrag={textareaDrag}
        textareaH={textareaH}
        inputAreaRef={inputAreaRef}
        llm={llm}
        openPanel={openPanel}
        togglePanel={togglePanel}
        docCount={activeDocs.length}
        ttsOn={ttsOn}
        sttOn={sttOn}
        onToggleTts={onToggleTts}
        onToggleStt={onToggleStt}
        handleSend={handleSend}
        handleCancel={handleCancel}
        handleNewConversation={handleNewConversation}
      />

      <ChatPopupPanel
        openPanel={openPanel}
        popupAnchor={popupAnchor}
        onSelectConversation={onSelectConversation}
        onClose={() => setOpenPanel(null)}
      />
    </div>
  );
}
