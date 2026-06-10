import { useState, useCallback } from "react";
import type { MutableRefObject, Dispatch, SetStateAction } from "react";
import type { Message } from "../types/api";
import type { ActiveDoc } from "../components/chat/types";
import type { useLLMWebSocket } from "../features/llm/useLLMWebSocket";

interface UseChatInferenceParams {
  messages: Message[];
  setMessages: Dispatch<SetStateAction<Message[]>>;
  appendMessage: (convId: number, msg: Message, index: number) => Promise<void>;
  cancelLoad: () => void;
  onSelectConversation?: (id: number | null) => void;
  conversationIdRef: MutableRefObject<number | null>;
  loadedConvRef: MutableRefObject<number | null>;
  modelPathRef: MutableRefObject<string>;
  llm: ReturnType<typeof useLLMWebSocket>;
  activeDocs: ActiveDoc[];
}

export function useChatInference({
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
}: UseChatInferenceParams) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  const doInference = useCallback(
    async (msgs: Message[]) => {
      if (!modelPathRef.current) {
        setError("Please select an LLM model in Settings first.");
        return;
      }
      setError(null);

      const activeDocIds = activeDocs.map((d) => d.id);

      try {
        const chunks = await llm.send(msgs, {
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
        const thinking = thinkingChunks.join("").trim();

        const nextIndex = msgs.length;
        if (fullResponse) {
          const assistantMsg: Message = {
            role: "assistant",
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
    [activeDocs, llm, appendMessage, conversationIdRef, modelPathRef],
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
        const { createConversation } = await import("../api/client");
        const result = await createConversation();
        conversationIdRef.current = result.conversation_id;
        onSelectConversation?.(result.conversation_id);
        loadedConvRef.current = result.conversation_id;
      } catch {
        // Proceed without a conversation ID; history won't survive a reload.
      }
    }

    const userMsgIndex = messages.length;
    const userMsg: Message = { role: "user", content: text };

    if (conversationIdRef.current !== null) {
      await appendMessage(conversationIdRef.current, userMsg, userMsgIndex);
    } else {
      setMessages((prev) => [...prev, userMsg]);
    }

    const newMessages: Message[] = [...messages, userMsg];
    await doInference(newMessages);
  }, [
    input,
    messages,
    llm.streaming,
    setMessages,
    appendMessage,
    onSelectConversation,
    doInference,
    conversationIdRef,
    loadedConvRef,
    modelPathRef,
  ]);

  const handleCancel = useCallback(() => llm.cancel(), [llm]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleNewConversation = useCallback(async () => {
    // Cancel any in-flight load so it can't overwrite the empty slate.
    cancelLoad();
    try {
      const { createConversation } = await import("../api/client");
      const result = await createConversation();
      const newId = result.conversation_id;
      conversationIdRef.current = newId;
      setMessages([]);
      loadedConvRef.current = newId;
      onSelectConversation?.(newId);
    } catch {
      // Creation failed (daemon/WebSocket unavailable). Reset to a blank
      // slate AND clear the persisted conversation id; otherwise the old id
      // is left in localStorage and a reload reloads the previous
      // conversation from history.
      conversationIdRef.current = null;
      loadedConvRef.current = null;
      setMessages([]);
      onSelectConversation?.(null);
    }
  }, [setMessages, cancelLoad, onSelectConversation, conversationIdRef, loadedConvRef]);

  return {
    input,
    setInput,
    error,
    setError,
    doInference,
    handleSend,
    handleCancel,
    handleKeyDown,
    handleNewConversation,
  };
}
