/**
 * Module-level singleton WebSocket client for the unified
 * ``/api/v1/events`` endpoint.
 *
 * Provides:
 * - Event subscription (``subscribe``/``unsubscribe``) for ``useEventBus``
 * - RPC request/response (``rpcRequest``, ``rpcRequestBlob``) for
 *   ``client-base.ts`` ``request()`` replacement
 *
 * All consumers share one WebSocket connection.
 */

// ---------------------------------------------------------------------------
// WS URL resolver
// ---------------------------------------------------------------------------

function wsUrl(): string {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const raw = (import.meta.env.VITE_API_BASE_URL as string) || "localhost:8188";
  const host = raw.replace(/^https?:\/\//, "");
  return `${proto}://${host}/api/v1/events`;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type EventBusCallback = (event: string, data: unknown) => void;

interface PendingRpc {
  resolve: (value: unknown) => void;
  reject: (err: Error) => void;
}

// ---------------------------------------------------------------------------
// Singleton state
// ---------------------------------------------------------------------------

let _ws: WebSocket | null = null;
let _connected = false;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _mountCount = 0;

// Event callbacks: event type → Set of callbacks
const _eventCallbacks = new Map<string, Set<EventBusCallback>>();

// Subscribed event types on the WS
const _subscribedEvents = new Set<string>();

// Pending RPC requests: request ID → PendingRpc
const _pendingRpc = new Map<string, PendingRpc>();

// Messages queued while WS is connecting
const _sendQueue: Record<string, unknown>[] = [];

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function _send(msg: Record<string, unknown>): void {
  if (_ws?.readyState === WebSocket.OPEN) {
    _ws.send(JSON.stringify(msg));
  } else if (_ws?.readyState === WebSocket.CONNECTING || !_ws) {
    _sendQueue.push(msg);
  }
}

function _subscribeEvents(events: string[]): void {
  const needed = events.filter((e) => !_subscribedEvents.has(e));
  if (needed.length === 0) return;
  for (const e of needed) _subscribedEvents.add(e);
  _send({ type: "subscribe", events: needed });
}

function _unsubscribeEvents(events: string[]): void {
  const active = events.filter((e) => _subscribedEvents.has(e));
  if (active.length === 0) return;
  for (const e of active) _subscribedEvents.delete(e);
  _send({ type: "unsubscribe", events: active });
}

function _reconnect(): void {
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }
  _reconnectTimer = setTimeout(_connect, 3000);
}

function _connect(): void {
  if (_ws) {
    const old = _ws;
    old.onclose = null;
    old.onerror = null;
    old.onmessage = null;
    old.close();
    _ws = null;
  }

  try {
    const socket = new WebSocket(wsUrl());
    _ws = socket;

    socket.onopen = () => {
      _connected = true;
      // Re-subscribe all currently tracked event types
      const events = [..._subscribedEvents];
      if (events.length > 0) {
        _send({ type: "subscribe", events });
      }
      // Flush queued messages
      const queue = _sendQueue.splice(0);
      for (const msg of queue) {
        _send(msg);
      }
    };

    socket.onmessage = (event: MessageEvent) => {
      // ── Binary frame: resolve the first pending binary RPC ──
      if (typeof event.data !== "string") {
        for (const [id, pending] of _pendingRpc) {
          _pendingRpc.delete(id);
          pending.resolve(event.data as Blob);
          return;
        }
        return;
      }

      // ── JSON frame ──
      try {
        const msg = JSON.parse(event.data) as {
          type?: string;
          event?: string;
          id?: string;
          data?: unknown;
          body?: unknown;
          status?: number;
          error?: string;
          binary?: boolean;
          headers?: Record<string, string>;
        };

        if (msg.type === "event" && msg.event) {
          const cbs = _eventCallbacks.get(msg.event);
          if (cbs) {
            for (const cb of cbs) {
              try {
                cb(msg.event, msg.data);
              } catch {
                // individual callback error must not break others
              }
            }
          }
        } else if (msg.type === "rpc_response" && msg.id) {
          const pending = _pendingRpc.get(msg.id);
          if (pending) {
            _pendingRpc.delete(msg.id);
            if (msg.binary === true) {
              // Binary response: re-register to expect the binary frame
              _pendingRpc.set(msg.id, pending);
            } else if (msg.status && msg.status >= 200 && msg.status < 300) {
              pending.resolve(msg.body);
            } else {
              const errMsg =
                msg.error ??
                ((msg.body as Record<string, unknown>)?.error as string) ??
                `RPC error ${msg.status}`;
              pending.reject(new Error(errMsg));
            }
          }
        }
        // Ignore subscribed, unsubscribed, pong, keepalive
      } catch {
        // ignore malformed messages
      }
    };

    socket.onclose = (event) => {
      _ws = null;
      _connected = false;
      // Reject all pending RPCs
      for (const [id, pending] of _pendingRpc) {
        _pendingRpc.delete(id);
        pending.reject(new Error("WebSocket disconnected"));
      }
      if (_mountCount > 0) _reconnect();
    };

    socket.onerror = () => {
      socket.close();
    };
  } catch {
    if (_mountCount > 0) _reconnect();
  }
}

function _disconnect(): void {
  if (_reconnectTimer) {
    clearTimeout(_reconnectTimer);
    _reconnectTimer = null;
  }
  if (_ws) {
    const old = _ws;
    old.onclose = null;
    old.onerror = null;
    old.onmessage = null;
    old.close();
    _ws = null;
  }
  _connected = false;
  // Reject all pending RPCs
  for (const [id, pending] of _pendingRpc) {
    _pendingRpc.delete(id);
    pending.reject(new Error("WebSocket disconnected"));
  }
}

// ---------------------------------------------------------------------------
// Public RPC helpers
// ---------------------------------------------------------------------------

let _rpcIdCounter = 0;

function _nextRpcId(): string {
  _rpcIdCounter++;
  return `rpc-${Date.now()}-${_rpcIdCounter}`;
}

/**
 * Send an RPC request and wait for the JSON response.
 * Replaces the old `fetch()`-based request() in client-base.ts.
 */
export function rpcRequest<T>(
  method: string,
  path: string,
  body?: Record<string, unknown>,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const id = _nextRpcId();
    _pendingRpc.set(id, {
      resolve: resolve as (value: unknown) => void,
      reject,
    });
    // Ensure the WS connection exists, even if no event bus consumers
    // have registered (RPC-only caller)
    if (!_ws || (_ws.readyState !== WebSocket.OPEN && _ws.readyState !== WebSocket.CONNECTING)) {
      _mountCount++;
      _connect();
    }
    _send({ type: "rpc", id, method, path, body: body ?? {} });
  });
}

/**
 * Send an RPC request and return the binary response as a Blob.
 * Used for images, audio, and other binary data.
 */
export function rpcRequestBlob(
  method: string,
  path: string,
  body?: Record<string, unknown>,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const id = _nextRpcId();
    _pendingRpc.set(id, {
      resolve: resolve as (value: unknown) => void,
      reject,
    });
    _send({ type: "rpc", id, method, path, body: body ?? {} });
  });
}

// ---------------------------------------------------------------------------
// Public event bus helpers
// ---------------------------------------------------------------------------

/**
 * Register an event callback.
 * Called by useEventBus on mount.
 */
export function registerEventCallbacks(
  events: string[],
  callback: EventBusCallback,
): void {
  _mountCount++;

  if (_mountCount === 1) _connect();

  for (const event of events) {
    let cbs = _eventCallbacks.get(event);
    if (!cbs) {
      cbs = new Set();
      _eventCallbacks.set(event, cbs);
    }
    cbs.add(callback);
  }

  _subscribeEvents(events);
}

/**
 * Unregister an event callback.
 * Called by useEventBus on unmount.
 */
export function unregisterEventCallbacks(
  events: string[],
  callback: EventBusCallback,
): void {
  for (const event of events) {
    const cbs = _eventCallbacks.get(event);
    if (cbs) {
      cbs.delete(callback);
      if (cbs.size === 0) {
        _eventCallbacks.delete(event);
      }
    }
  }

  const orphaned = events.filter((e) => !_eventCallbacks.has(e));
  if (orphaned.length > 0) _unsubscribeEvents(orphaned);

  _mountCount--;
  if (_mountCount === 0) _disconnect();
}
