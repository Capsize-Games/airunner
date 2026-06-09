import { useCallback } from "react";
import type { MutableRefObject, Dispatch, SetStateAction } from "react";
import type { Message } from "../types/api";

interface UseChatMessageActionsParams {
  conversationIdRef: MutableRefObject<number | null>;
  messages: Message[];
  setMessages: Dispatch<SetStateAction<Message[]>>;
  deleteMessagesAfter: (convId: number, index: number) => Promise<void>;
  setError: Dispatch<SetStateAction<string | null>>;
  doInference: (msgs: Message[]) => Promise<void>;
}

export function useChatMessageActions({
  conversationIdRef,
  messages,
  setMessages,
  deleteMessagesAfter,
  setError,
  doInference,
}: UseChatMessageActionsParams) {
  const handleDeleteMessage = useCallback(
    async (index: number) => {
      const convId = conversationIdRef.current;
      if (convId !== null) {
        try {
          const { truncateConversation } = await import("../api/chat");
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
    [conversationIdRef, setMessages, deleteMessagesAfter, setError],
  );

  const handleSubmitEdit = useCallback(
    async (index: number, newContent: string) => {
      const convId = conversationIdRef.current;
      if (convId !== null) {
        try {
          const { truncateConversation } = await import("../api/chat");
          await truncateConversation(convId, index);
        } catch {
          setError("Failed to truncate conversation on server. Edit aborted.");
          return;
        }
      }
      const edited: Message[] = [
        ...messages.slice(0, index),
        { role: "user", content: newContent },
      ];
      setMessages(edited);
      await doInference(edited);
    },
    [conversationIdRef, messages, setMessages, setError, doInference],
  );

  const handleCopyMessage = useCallback((content: string) => {
    navigator.clipboard.writeText(content).catch(() => {});
  }, []);

  const handlePlayMessage = useCallback(async (content: string) => {
    try {
      const { synthesizeTTS } = await import("../api/chat");
      const blob = await synthesizeTTS(content);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      // TTS failed — silently ignore
    }
  }, []);

  return {
    handleDeleteMessage,
    handleSubmitEdit,
    handleCopyMessage,
    handlePlayMessage,
  };
}
