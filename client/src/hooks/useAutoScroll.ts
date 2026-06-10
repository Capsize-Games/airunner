import { useEffect, useRef, useCallback } from "react";

/**
 * Smart auto-scroll hook that mimics the scroll behavior of Claude, Gemini,
 * and ChatGPT:
 *
 * 1. When streaming starts (user submits), always scroll to bottom.
 * 2. As new tokens stream in, auto-scroll only if the user is already
 *    near the bottom of the container.
 * 3. If the user scrolls up during streaming, auto-scroll is paused.
 * 4. If the user scrolls back to the bottom, auto-scroll resumes.
 *
 * @param containerRef - React ref to the scrollable DOM element.
 * @param isStreaming  - Whether the LLM is currently streaming a response.
 * @param deps         - Additional values that should trigger an auto-scroll
 *                       check when they change (e.g. streamBuffer).
 */
export function useAutoScroll(
  containerRef: React.RefObject<HTMLDivElement | null>,
  isStreaming: boolean,
  deps: unknown[],
) {
  const userScrolledAwayRef = useRef(false);
  const wasStreamingRef = useRef(isStreaming);

  /** Returns true when the user is within 40 px of the bottom. */
  const isAtBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return true;
    const { scrollTop, scrollHeight, clientHeight } = el;
    return scrollHeight - scrollTop - clientHeight < 40;
  }, [containerRef]);

  /** Snap the container to the bottom immediately. */
  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [containerRef]);

  /** Attach this to the container's `onScroll` handler. */
  const handleScroll = useCallback(() => {
    userScrolledAwayRef.current = !isAtBottom();
  }, [isAtBottom]);

  // ── On streaming start → always scroll to bottom ────────────────
  useEffect(() => {
    if (isStreaming && !wasStreamingRef.current) {
      userScrolledAwayRef.current = false;
      scrollToBottom();
    }
    wasStreamingRef.current = isStreaming;
  }, [isStreaming, scrollToBottom]);

  // ── On content change → auto-scroll only if at bottom ───────────
  useEffect(() => {
    if (!userScrolledAwayRef.current && isStreaming) {
      scrollToBottom();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { scrollToBottom, handleScroll };
}
