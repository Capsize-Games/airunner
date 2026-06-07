import { rpcRequest } from "../features/api/WsApiClient";
import type { JsonObject, StreamChunk } from "../types/api";

/**
 * Resolve the WebSocket host for any WS endpoint.
 *
 * In dev mode the Vite proxy forwards /api/v1/* to the backend, so we
 * use the page's own host (port 5173).  In production the caller must
 * set VITE_API_BASE_URL; the fallback is localhost:8188.
 */
export function wsHost(): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (raw) {
    return raw.replace(/^https?:\/\//, "");
  }
  // Dev mode — go through the Vite proxy.
  return location.host;
}

const REQUEST_TIMEOUT_MS = 180_000; // 3 minutes

/**
 * Send an HTTP-style request over the shared WebSocket RPC channel.
 *
 * The signature is identical to the old ``fetch()``-based version so
 * all callers work without changes.  The underlying transport is now
 * a single persistent WebSocket connection.
 */
export async function request<T>(
  method: string,
  path: string,
  body?: JsonObject,
): Promise<T> {
  const timer = setTimeout(() => {
    throw new Error(`Request timed out: ${method} ${path}`);
  }, REQUEST_TIMEOUT_MS);
  try {
    return await rpcRequest<T>(method, path, body);
  } finally {
    clearTimeout(timer);
  }
}
