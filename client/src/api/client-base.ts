import { rpcRequest } from "../features/api/WsApiClient";
import type { JsonObject, StreamChunk } from "../types/api";

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
