/**
 * WebSocket hook for TTS synthesis via ``/api/v1/tts/ws``.
 *
 * Maintains a persistent connection and provides a promise-based
 * ``synthesize()`` method that returns audio as a ``Blob``.
 *
 * Usage::
 *
 *   const tts = useTTSWebSocket();
 *   const blob = await tts.synthesize("Hello world", { voice: "en-US" });
 *   const url = URL.createObjectURL(blob);
 */

import { useState, useRef, useCallback, useEffect } from "react";

// ---------------------------------------------------------------------------
// WS URL resolver
// ---------------------------------------------------------------------------

import { wsHost } from "../../api/client-base";

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${wsHost()}/api/v1/tts/ws`;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface TTSOptions {
  voice?: string;
  speed?: number;
}

export function useTTSWebSocket() {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  // Per-synthesis promise callbacks
  const pendingResolve =
    useRef<((blob: Blob) => void) | null>(null);
  const pendingReject =
    useRef<((err: Error) => void) | null>(null);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      const socket = new WebSocket(wsUrl());
      wsRef.current = socket;

      socket.onopen = () => {
        if (mountedRef.current) setReady(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type = data.type;

          if (type === "audio") {
            const raw = data.data as string;
            const binary = atob(raw);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
              bytes[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: "audio/wav" });
            if (pendingResolve.current) {
              pendingResolve.current(blob);
              pendingResolve.current = null;
              pendingReject.current = null;
            }
          } else if (type === "error") {
            const msg = data.message ?? "TTS failed";
            setError(msg);
            if (pendingReject.current) {
              pendingReject.current(new Error(msg));
              pendingResolve.current = null;
              pendingReject.current = null;
            }
          }
        } catch {
          // ignore malformed
        }
      };

      socket.onclose = (event) => {
        wsRef.current = null;
        setReady(false);
        if (mountedRef.current && !event.wasClean) {
          reconnectTimerRef.current = setTimeout(connect, 5000);
        }
      };

      socket.onerror = () => {
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
    connect();
    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.onmessage = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const synthesize = useCallback(
    (text: string, options?: TTSOptions): Promise<Blob> => {
      return new Promise((resolve, reject) => {
        pendingResolve.current = resolve;
        pendingReject.current = reject;
        setError(null);
        sendMessage({
          type: "synthesize",
          text,
          voice: options?.voice,
          speed: options?.speed ?? 1.0,
        });
      });
    },
    [sendMessage],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    ready,
    error,
    synthesize,
    clearError,
  };
}
