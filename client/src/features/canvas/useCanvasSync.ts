import { useEffect, useRef, useCallback, useState } from "react";
import { wsHost } from "../../api/client-base";

const WS_RECONNECT_DELAY = 1000;
const WS_MAX_RECONNECT_DELAY = 10_000;

function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${wsHost()}${path}`;
}

export interface UseCanvasSyncOptions {
  /** Called when the server sends the full document (on connect). */
  onDocument: (json: string | null) => void;
}

export interface UseCanvasSyncReturn {
  /** Whether the WebSocket is currently connected. */
  connected: boolean;
  /** Send a canvas document snapshot to the server instantly. */
  send: (document: string) => void;
}

/**
 * Hook that manages a persistent WebSocket to the canvas document endpoint.
 *
 * - Connects on mount, reconnects on disconnect.
 * - Sends document snapshots immediately (no debounce).
 * - Calls `onDocument` when the server pushes the stored document.
 */
export function useCanvasSync({
  onDocument,
}: UseCanvasSyncOptions): UseCanvasSyncReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connected, setConnected] = useState(false);
  const onDocumentRef = useRef(onDocument);
  onDocumentRef.current = onDocument;

  // Accumulator: queue messages while connecting so nothing is lost.
  const queueRef = useRef<string[]>([]);
  const sendImmediate = useCallback((msg: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(msg);
      return true;
    }
    // Queue for later delivery.
    queueRef.current.push(msg);
    return false;
  }, []);

  // Flush any queued messages once the socket opens.
  const flushQueue = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const q = queueRef.current;
    queueRef.current = [];
    for (const msg of q) {
      ws.send(msg);
    }
  }, []);

  useEffect(() => {
    let stopped = false;

    // Delay initial connection so the server has time to accept WebSocket
    // upgrades during page load, avoiding noisy console errors.
    const connect = (delay = 1000) => {
      if (stopped) return;

      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }

      if (delay > 0) {
        reconnectTimer.current = setTimeout(
          () => connect(0),
          Math.min(delay, WS_MAX_RECONNECT_DELAY),
        );
        return;
      }

      // Close any stale socket.
      const old = wsRef.current;
      if (old && old.readyState <= WebSocket.OPEN) {
        try { old.close(); } catch { /* ignore */ }
      }

      const ws = new WebSocket(wsUrl("/api/v1/canvas/ws"));
      wsRef.current = ws;

      ws.onopen = () => {
        if (stopped) {
          ws.close();
          return;
        }
        setConnected(true);
        flushQueue();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "document") {
            onDocumentRef.current(data.document ?? null);
          }
        } catch {
          // Malformed message — ignore.
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        if (!stopped) {
          // Reconnect with exponential back-off.
          const nextDelay = delay === 0
            ? WS_RECONNECT_DELAY
            : Math.min(delay * 2, WS_MAX_RECONNECT_DELAY);
          connect(nextDelay);
        }
      };

      ws.onerror = () => {
        // onclose will fire after onerror, triggering reconnect.
        ws.close();
      };
    };

    connect();

    return () => {
      stopped = true;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      if (wsRef.current) {
        try { wsRef.current.close(); } catch { /* ignore */ }
        wsRef.current = null;
      }
    };
  }, [flushQueue]);

  const send = useCallback(
    (document: string) => {
      sendImmediate(JSON.stringify({ document }));
    },
    [sendImmediate],
  );

  return { connected, send };
}
