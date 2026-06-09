import type { StreamChunk } from "../../types/api";
import type { ToolStatusEvent } from "./useLLMWebSocket";

export interface WsMessageCallbacks {
  onChunk: ((chunk: StreamChunk) => void) | null;
  onDone: (() => void) | null;
  onError: ((msg: string) => void) | null;
  setError: (msg: string) => void;
  setStreaming: (v: boolean) => void;
  setStreamBuffer: (fn: (prev: string) => string) => void;
  setThinkingBuffer: (fn: (prev: string) => string) => void;
  setActiveTools: (fn: (prev: ToolStatusEvent[]) => ToolStatusEvent[]) => void;
}

export function handleWsMessage(raw: string, cbs: WsMessageCallbacks): void {
  let data: { type?: string; content?: string; done?: boolean; error?: string };
  try {
    data = JSON.parse(raw) as typeof data;
  } catch {
    return;
  }

  if (data.type === "error") {
    const msg = data.error ?? data.content ?? "LLM error";
    cbs.setError(msg);
    cbs.onError?.(msg);
    cbs.setStreaming(false);
    cbs.onDone?.();
    return;
  }

  if (data.type === "tool_status") {
    const ev = data as unknown as ToolStatusEvent;
    cbs.setActiveTools((prev) => {
      const filtered = prev.filter((t) => t.tool_id !== ev.tool_id);
      if (ev.status === "completed" || ev.status === "error") return filtered;
      return [...filtered, ev];
    });
    return;
  }

  if (data.type === "thinking") {
    cbs.setThinkingBuffer((prev) => prev + (data.content ?? ""));
    const chunk: StreamChunk = {
      token: data.content ?? "",
      message_type: "thinking",
      done: data.done ?? false,
    };
    cbs.onChunk?.(chunk);
    if (data.done) {
      cbs.setThinkingBuffer(() => "");
    }
    return;
  }

  const content = data.content ?? "";
  cbs.setStreamBuffer((prev) => prev + content);
  const chunk: StreamChunk = { token: content, done: data.done ?? false };
  cbs.onChunk?.(chunk);

  if (data.done) {
    cbs.setStreamBuffer(() => "");
    cbs.setThinkingBuffer(() => "");
    cbs.setActiveTools(() => []);
    cbs.onDone?.();
    cbs.setStreaming(false);
  }
}
