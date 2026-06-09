import { useState, useRef, useCallback, useEffect } from "react";

export function useChatTextareaResize() {
  const [textareaH, setTextareaH] = useState(() => {
    try { return Number(localStorage.getItem("chat_textarea_h")) || 200; }
    catch { return 220; }
  });
  const textareaDrag = useRef(false);
  const textareaStartY = useRef(0);
  const textareaStartH = useRef(0);

  const handleTextareaResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    textareaDrag.current = true;
    textareaStartY.current = e.clientY;
    textareaStartH.current = textareaH;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";

    const onMove = (ev: MouseEvent) => {
      if (!textareaDrag.current) return;
      const delta = ev.clientY - textareaStartY.current;
      const newH = Math.max(200, Math.min(500, textareaStartH.current - delta));
      setTextareaH(newH);
    };

    const onUp = () => {
      textareaDrag.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [textareaH]);

  useEffect(() => {
    try { localStorage.setItem("chat_textarea_h", String(textareaH)); } catch { /* */ }
  }, [textareaH]);

  return { textareaH, textareaDrag, handleTextareaResize };
}
