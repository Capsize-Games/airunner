import { useState, useCallback, useRef } from "react";
import type { Message } from "../types/api";

// ── useConversationMessages ───────────────────────────────────────────────────
// Server-only fetches.  Keeps the append-only strategy — messages are never
// overwritten based on timestamp comparison.

export function useConversationMessages() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const pendingLoadId = useRef<number | null>(null);

  const cancelLoad = useCallback(() => {
    pendingLoadId.current = null;
    setLoading(false);
  }, []);

  const load = useCallback(async (conversationId: number) => {
    pendingLoadId.current = conversationId;
    setLoading(true);

    try {
      const { loadConversation } = await import("../api/client");
      const session = await loadConversation(conversationId);
      const rawMsgs = session.messages ?? [];

      if (pendingLoadId.current !== conversationId) return;

      const mapped: Message[] = rawMsgs.map(
        (raw: Record<string, unknown>) => {
          let content = String(raw.content ?? "");
          if (raw.is_bot && content.toLowerCase().startsWith("assistant ")) {
            content = content.slice(10);
          }
          const tc =
            String(raw.thinking_content ?? "") ||
            String(raw.pre_tool_thinking ?? "");
          return {
            role: (raw.is_bot ? "assistant" : "user") as Message["role"],
            content,
            thinking_content: tc || undefined,
            created_at: raw.created_at ? String(raw.created_at) : undefined,
          };
        },
      );

      if (rawMsgs.length > 0) {
        setMessages(mapped);
      } else {
        setMessages([]);
      }
    } catch {
      /* network unavailable */
    } finally {
      if (pendingLoadId.current === conversationId) setLoading(false);
    }
  }, []);

  const appendMessage = useCallback(async (
    _conversationId: number,
    message: Message,
    _index: number,
  ) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const deleteMessagesAfter = useCallback(
    async (_conversationId: number, index: number) => {
      setMessages((prev) => prev.slice(0, index));
    },
    [],
  );

  const clear = useCallback(() => setMessages([]), []);

  return {
    messages,
    loading,
    setMessages,
    load,
    cancelLoad,
    appendMessage,
    deleteMessagesAfter,
    clear,
  };
}
