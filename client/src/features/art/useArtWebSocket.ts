import { useState, useRef, useCallback, useEffect } from "react";

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const raw = (import.meta.env.VITE_API_BASE_URL as string) || "localhost:8188";
  const host = raw.replace(/^https?:\/\//, "");
  return `${proto}://${host}/api/v1/art/ws`;
}

export interface ArtWebSocketState {
  generating: boolean;
  progress: number;
  jobId: string | null;
}

export interface ArtGenerateParams {
  prompt: string;
  negativePrompt?: string;
  seed?: number;
  artModel?: string;
  artVersion?: string;
  scheduler?: string;
  width?: number;
  height?: number;
  onComplete?: (imageBase64: string) => void;
}

export function useArtWebSocket() {
  const [state, setState] = useState<ArtWebSocketState>({
    generating: false,
    progress: 0,
    jobId: null,
  });
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const mountedRef = useRef(true);
  const pendingResolve = useRef<((image: string) => void) | null>(null);
  const pendingReject = useRef<((err: Error) => void) | null>(null);
  const sendQueueRef = useRef<Record<string, unknown>[]>([]);

  const flushQueue = useCallback(() => {
    const q = sendQueueRef.current;
    sendQueueRef.current = [];
    for (const msg of q) {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(msg));
      }
    }
  }, []);

  const sendMessage = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      sendQueueRef.current.push(msg);
    }
  }, []);

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
        flushQueue();
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const type = data.type;

          if (type === "ack") {
            setState((prev) => ({
              ...prev,
              generating: true,
              progress: 0,
              jobId: data.job_id ?? prev.jobId,
            }));
          } else if (type === "progress") {
            setState((prev) => ({
              ...prev,
              progress: data.progress ?? prev.progress,
            }));
          } else if (type === "complete") {
            setState((prev) => ({
              ...prev,
              generating: false,
              progress: 100,
              jobId: null,
            }));
            if (data.image && pendingResolve.current) {
              pendingResolve.current(data.image);
              pendingResolve.current = null;
              pendingReject.current = null;
            }
          } else if (type === "cancelled") {
            setState((prev) => ({
              ...prev,
              generating: false,
              progress: 0,
              jobId: null,
            }));
            if (pendingReject.current) {
              pendingReject.current(new Error("Cancelled"));
              pendingResolve.current = null;
              pendingReject.current = null;
            }
          } else if (type === "error") {
            setState((prev) => ({
              ...prev,
              generating: false,
              progress: 0,
              jobId: null,
            }));
            if (pendingReject.current) {
              pendingReject.current(new Error(data.error || "Unknown"));
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
  }, []);

  const generate = useCallback(
    (params: ArtGenerateParams): Promise<string> => {
      // Lazily connect if not already connected
      connect();
      return new Promise((resolve, reject) => {
        pendingResolve.current = resolve;
        pendingReject.current = reject;
        sendMessage({
          type: "generate",
          prompt: params.prompt,
          negative_prompt: params.negativePrompt,
          seed: params.seed,
          model: params.artModel,
          version: params.artVersion,
          scheduler: params.scheduler,
          width: params.width,
          height: params.height,
        });
      });
    },
    [sendMessage, connect],
  );

  const cancel = useCallback(() => {
    const jid = state.jobId;
    if (jid) {
      // Lazily connect if not already connected
      connect();
      sendMessage({ type: "cancel", job_id: jid });
    }
    setState((prev) => ({
      ...prev,
      generating: false,
      progress: 0,
      jobId: null,
    }));
  }, [sendMessage, connect, state.jobId]);

  const unload = useCallback(
    (modelId: string) => {
      // Lazily connect if not already connected
      connect();
      sendMessage({ type: "unload", model_id: modelId });
    },
    [sendMessage, connect],
  );

  return {
    ...state,
    generate,
    cancel,
    unload,
  };
}
