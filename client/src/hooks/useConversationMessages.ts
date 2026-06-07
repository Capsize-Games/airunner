import { useState, useCallback } from "react";
import { useDb } from "../db/DbContext";
import type { Message } from "../types/api";
import type { CachedMessage } from "../db/db";

function buildMessageId(conversationId: number, index: number): string {
  return `${conversationId}_${index}`;
}

function toStored(
  raw: Record<string, unknown>,
  conversationId: number,
  index: number,
): CachedMessage {
  let content = String(raw.content ?? "");
  if (raw.is_bot && content.toLowerCase().startsWith("assistant ")) {
    content = content.slice(10);
  }
  return {
    id: buildMessageId(conversationId, index),
    conversationId,
    sortIndex: index,
    role: raw.is_bot ? "assistant" : "user",
    content,
    thinking_content: raw.thinking_content
      ? String(raw.thinking_content)
      : undefined,
    created_at: raw.created_at ? String(raw.created_at) : undefined,
  };
}

// ── useConversationMessages ───────────────────────────────────────────────────
// Append-only strategy: server records are always merged in by ID, never
// overwritten via timestamp.  The client never deletes messages from cache
// based on a timestamp comparison — only an explicit invalidation clears them.

export function useConversationMessages() {
  const db = useDb();
  const [messages, setMessages] = useState<Message[]>([]);

  const load = useCallback(async (conversationId: number) => {
    if (db) {
      // Serve from cache first if available.
      const cached = await db.messages
        .where("conversationId")
        .equals(conversationId)
        .sortBy("sortIndex");

      if (cached.length > 0) {
        setMessages(
          cached.map((m) => ({
            role: m.role,
            content: m.content,
            thinking_content: m.thinking_content,
            created_at: m.created_at,
          })),
        );
      }
    }

    // Always fetch from server for the authoritative message list.
    try {
      const { selectConversation } = await import("../api/client");
      const session = await selectConversation(conversationId);
      const rawMsgs = session.messages ?? [];

      // The server attaches `pre_tool_thinking` to the next assistant
      // message after a tool-call metadata row.  Use that if the direct
      // `thinking_content` field is not present.
      const mapped: Message[] = rawMsgs.map(
        (raw: Record<string, unknown>, i) => {
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
      setMessages(mapped);

      // Persist to IndexedDB (append-only via bulkPut keyed by index).
      if (db) {
        const stored = rawMsgs.map((raw, i) =>
          toStored(raw as Record<string, unknown>, conversationId, i),
        );
        await db.messages.bulkPut(stored);
      }
    } catch {
      /* network unavailable — stale cache already shown */
    }
  }, [db]);

  const appendMessage = useCallback(async (
    conversationId: number,
    message: Message,
    index: number,
  ) => {
    setMessages((prev) => [...prev, message]);
    if (db) {
      await db.messages.put({
        id: buildMessageId(conversationId, index),
        conversationId,
        sortIndex: index,
        ...message,
      });
    }
  }, [db]);

  const deleteMessagesAfter = useCallback(
    async (conversationId: number, index: number) => {
      setMessages((prev) => prev.slice(0, index));
      if (db) {
        const toRemove = await db.messages
          .where("conversationId")
          .equals(conversationId)
          .filter((m) => m.sortIndex >= index)
          .toArray();
        const ids = toRemove.map((m) => m.id);
        if (ids.length > 0) {
          await db.messages.bulkDelete(ids);
        }
      }
    },
    [db],
  );

  const clear = useCallback(() => setMessages([]), []);

  return {
    messages,
    setMessages,
    load,
    appendMessage,
    deleteMessagesAfter,
    clear,
  };
}
