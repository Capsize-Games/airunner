// ── Canvas Stage Keyboard Shortcuts ──────────────────────────────────────
import { useEffect } from "react";
import type { ActiveTool } from "../canvasTypes";

interface Params {
  onUndo: () => void;
  onRedo: () => void;
  setActiveTool: (tool: ActiveTool) => void;
}

export function keyboard({
  onUndo,
  onRedo,
  setActiveTool,
}: Params) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const tag = target.tagName;
      if (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        tag === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }
      if (
        (e.ctrlKey || e.metaKey) &&
        e.key === "z" &&
        !e.shiftKey
      ) {
        e.preventDefault();
        onUndo();
        return;
      }
      if (
        (e.ctrlKey || e.metaKey) &&
        (e.key === "y" || (e.key === "z" && e.shiftKey))
      ) {
        e.preventDefault();
        onRedo();
        return;
      }
      if (e.key === "b" || e.key === "B")
        setActiveTool("brush");
      else if (e.key === "e" || e.key === "E")
        setActiveTool("eraser");
      else if (e.key === "m" || e.key === "M")
        setActiveTool("mask");
      else if (e.key === "v" || e.key === "V")
        setActiveTool("move");
      else if (e.key === "s" || e.key === "S")
        setActiveTool("select");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onUndo, onRedo, setActiveTool]);
}
