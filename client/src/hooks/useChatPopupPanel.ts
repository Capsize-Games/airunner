import { useState, useRef, useEffect, useCallback } from "react";
import type { ChatPanel } from "../components/chat/types";

export function useChatPopupPanel() {
  const [openPanel, setOpenPanel] = useState<ChatPanel>(null);
  const [popupAnchor, setPopupAnchor] = useState<{
    left: number;
    bottom: number;
    width: number;
    height: number;
  } | null>(null);
  const inputAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!openPanel) return;
    if (inputAreaRef.current) {
      const rect = inputAreaRef.current.getBoundingClientRect();
      const belowInputArea = window.innerHeight - rect.bottom + 66;
      setPopupAnchor({
        left: rect.left,
        bottom: belowInputArea,
        width: rect.width,
        height: Math.min(480, rect.bottom - 74),
      });
    }
  }, [openPanel]);

  useEffect(() => {
    if (!openPanel) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const insideInputArea = inputAreaRef.current?.contains(target);
      const insidePopup = document
        .getElementById("chat-panel-popup")
        ?.contains(target);
      if (!insideInputArea && !insidePopup) setOpenPanel(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [openPanel]);

  useEffect(() => {
    const handler = () => setOpenPanel(null);
    window.addEventListener("chat-picker-opened", handler);
    return () => window.removeEventListener("chat-picker-opened", handler);
  }, []);

  const togglePanel = useCallback((panel: NonNullable<ChatPanel>) => {
    setOpenPanel((prev) => (prev === panel ? null : panel));
  }, []);

  return { openPanel, popupAnchor, setOpenPanel, togglePanel, inputAreaRef };
}
