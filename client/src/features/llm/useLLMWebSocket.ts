/**
 * WebSocket hook for LLM chat streaming via ``/api/v1/llm/stream``.
 *
 * Usage::
 *
 *   const llm = useLLMWebSocket();
 *   llm.send(messages, { model: "..." });
 *   // llm.streaming, llm.streamBuffer, llm.thinkingBuffer, llm.error
 */

import { useState, useRef, useCallback, useEffect } from "react";
import type { Message, StreamChunk } from "../../types/api";

// ---------------------------------------------------------------------------
// WS URL resolver
// ---------------------------------------------------------------------------

import { wsHost } from "../../api/client-base";

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${wsHost()}/api/v1/llm/stream`;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface LLMOptions {
  model?: string;
  temperature?: number;
  max_tokens?: number;
  conversation_id?: number;
  active_document_ids?: number[];
}

export function useLLMWebSocket() {
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [thinkingBuffer, setThinkingBuffer] = useState("");
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  // Incremented each time we start a fresh connection so stale
  // callbacks (from orphaned sockets during StrictMode) are ignored.
  const connGenRef = useRef(0);

  // Messages queued while WS is connecting
  const sendQueueRef = useRef<Record<string, unknown>[]>([]);

  // Callbacks set per-stream (not per-hook-lifetime) so we can read
  // the latest values without re-creating the WS connection.
  const onChunkRef = useRef<
    ((chunk: StreamChunk) => void) | null
  >(null);
  const onDoneRef = useRef<(() => void) | null>(null);
  const onErrorRef = useRef<((msg: string) => void) | null>(null);

  const sendMessage = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      sendQueueRef.current.push(msg);
    }
  }, []);

  // Flush queued messages when the socket opens
  const flushQueue = useCallback(() => {
    const q = sendQueueRef.current;
    sendQueueRef.current = [];
    for (const msg of q) {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(msg));
      }
    }
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    // Don't disrupt an in-flight connection.
    if (wsRef.current &&
        (wsRef.current.readyState === WebSocket.OPEN ||
         wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    const gen = ++connGenRef.current;

    try {
      const socket = new WebSocket(wsUrl());
      wsRef.current = socket;

      socket.onopen = () => {
        if (gen !== connGenRef.current) return; // stale
        flushQueue();
      };

      socket.onmessage = (event) => {
        if (gen !== connGenRef.current) return; // stale
        try {
          const data = JSON.parse(event.data) as {
            type?: string;
            content?: string;
            done?: boolean;
            error?: string;
          };

          if (data.type === "error") {
            const msg = data.error ?? data.content ?? "LLM error";
            setError(msg);
            onErrorRef.current?.(msg);
            setStreaming(false);
            onDoneRef.current?.();
            return;
          }

          if (data.type === "thinking") {
            setThinkingBuffer(data.content ?? "");
            const chunk: StreamChunk = {
              token: data.content ?? "",
              message_type: "thinking",
              done: data.done ?? false,
            };
            onChunkRef.current?.(chunk);
            if (data.done) {
              setStreamBuffer("");
              setThinkingBuffer("");
              onDoneRef.current?.();
              setStreaming(false);
            }
            return;
          }

          // Regular chunk
          const content = data.content ?? "";
          setStreamBuffer((prev) => prev + content);
          const chunk: StreamChunk = {
            token: content,
            done: data.done ?? false,
          };
          onChunkRef.current?.(chunk);

          if (data.done) {
            // Clear live buffers so the StreamingBubble doesn't
            // linger after the turn completes.  The final content
            // is now carried by the assistant Message in state.
            setStreamBuffer("");
            setThinkingBuffer("");
            onDoneRef.current?.();
            setStreaming(false);
          }
        } catch {
          // ignore malformed
        }
      };

      socket.onclose = (event) => {
        if (gen !== connGenRef.current) return; // stale
        wsRef.current = null;
        if (mountedRef.current && !event.wasClean) {
          reconnectTimerRef.current = setTimeout(connect, 5000);
        }
      };

      socket.onerror = () => {
        if (gen !== connGenRef.current) return; // stale
        socket.close();
      };
    } catch {
      if (mountedRef.current) {
        reconnectTimerRef.current = setTimeout(connect, 5000);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      // Bump gen so any orphaned socket callbacks are ignored
      connGenRef.current++;
      if (wsRef.current) {
        // Orphan a CONNECTING socket instead of force-closing it
        // to avoid "WebSocket is closed before the connection is
        // established" errors (e.g. React StrictMode double-mount).
        if (wsRef.current.readyState !== WebSocket.CONNECTING) {
          wsRef.current.close();
        }
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.onmessage = null;
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, []);


  const send = useCallback(
    (
      messages: Message[],
      options?: LLMOptions,
    ): Promise<StreamChunk[]> => {
      return new Promise((resolve, reject) => {
        const chunks: StreamChunk[] = [];

        onChunkRef.current = (chunk: StreamChunk) => {
          chunks.push(chunk);
        };

        onDoneRef.current = () => {
          onChunkRef.current = null;
          onDoneRef.current = null;
          onErrorRef.current = null;
          resolve(chunks);
        };

        onErrorRef.current = (msg: string) => {
          onChunkRef.current = null;
          onDoneRef.current = null;
          onErrorRef.current = null;
          reject(new Error(msg));
        };

        setStreaming(true);
        setStreamBuffer("");
        setThinkingBuffer("");
        setError(null);

        // Lazily connect if not already connected
        connect();

        sendMessage({
          type: "chat",
          messages: messages.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          model: options?.model,
          temperature: options?.temperature ?? 0.7,
          max_tokens: options?.max_tokens,
          conversation_id: options?.conversation_id,
          active_document_ids: options?.active_document_ids,
        });
      });
    },
    [sendMessage, connect],
  );

  const cancel = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "cancel" }));
    }
    setStreaming(false);
    setStreamBuffer("");
    setThinkingBuffer("");
    onChunkRef.current = null;
    onDoneRef.current = null;
    onErrorRef.current = null;
  }, []);

  return {
    streaming,
    streamBuffer,
    thinkingBuffer,
    error,
    send,
    cancel,
    setError,
  };
}
