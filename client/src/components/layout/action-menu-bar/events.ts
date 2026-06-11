// ── Action Menu Events ──────────────────────────────────────────────────
import { useEffect, useRef } from "react";

export type ActionMenuEvent =
  | { type: "file:new-document" }
  | { type: "edit:undo" }
  | { type: "edit:redo" }
  | { type: "edit:cut" }
  | { type: "edit:copy" }
  | { type: "edit:paste" }
  | { type: "edit:delete" }
  | { type: "edit:preferences" }
  | { type: "select:all" }
  | { type: "select:none" }
  | { type: "view:toggle-chat" }
  | { type: "view:toggle-canvas" }
  | { type: "view:toggle-civitai" }
  | { type: "view:toggle-ruler" }
  | { type: "view:toggle-grid" };

/** Dispatch a menu action as a window CustomEvent. */
export function dispatchMenuAction(
  action: ActionMenuEvent,
): void {
  window.dispatchEvent(
    new CustomEvent<ActionMenuEvent>(
      "airunner:menu-action",
      { detail: action },
    ),
  );
}

/** Hook to listen for menu actions from anywhere in the tree. */
export function useMenuAction(
  handler: (action: ActionMenuEvent) => void,
): void {
  const handlerRef = useRef(handler);
  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEffect(() => {
    const listener = (e: Event) => {
      const { detail } =
        e as CustomEvent<ActionMenuEvent>;
      handlerRef.current(detail);
    };
    window.addEventListener(
      "airunner:menu-action",
      listener,
    );
    return () =>
      window.removeEventListener(
        "airunner:menu-action",
        listener,
      );
  }, []);
}
