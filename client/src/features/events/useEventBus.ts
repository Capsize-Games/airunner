/**
 * React hook that subscribes to real-time events through the shared
 * ``WsApiClient`` singleton (one WebSocket connection for all consumers).
 *
 * Usage::
 *
 *   function ImageBrowser() {
 *     useEventBus(["images"], (event, data) => {
 *       if (data.type === "reload") onReload();
 *     });
 *   }
 *
 * The underlying WebSocket connection is managed by ``WsApiClient``
 * and is shared with ``rpcRequest()`` consumers.
 */

import { useEffect, useRef } from "react";
import {
  registerEventCallbacks,
  unregisterEventCallbacks,
} from "../api/WsApiClient";

type EventBusCallback = (event: string, data: unknown) => void;

/**
 * Subscribe to real-time events through the shared event WebSocket.
 *
 * @param events - List of event types to subscribe to (e.g. ``["images"]``)
 * @param callback - Called with ``(eventType, data)`` for each event
 */
export function useEventBus(
  events: string[],
  callback: EventBusCallback,
): void {
  const callbackRef = useRef<EventBusCallback>(callback);
  callbackRef.current = callback;

  useEffect(() => {
    // Use a stable callback wrapper that delegates to the ref
    const wrapper: EventBusCallback = (event, data) => {
      callbackRef.current(event, data);
    };
    registerEventCallbacks(events, wrapper);
    return () => {
      unregisterEventCallbacks(events, wrapper);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
