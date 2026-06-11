import { createPortal } from "react-dom";
import LucideIcon from "../../shared/LucideIcon";

interface PromptSettingsPopupProps {
  anchor: { left: number; bottom: number } | null;
  saving: boolean;
  promptEmpty: boolean;
  onNewPrompt: () => void;
  onSavePrompt: () => void;
  onLoadSavedPrompts: () => void;
}

export default function PromptSettingsPopup({
  anchor,
  saving,
  promptEmpty,
  onNewPrompt,
  onSavePrompt,
  onLoadSavedPrompts,
}: PromptSettingsPopupProps) {
  if (!anchor) return null;

  return createPortal(
    <div
      id="art-prompt-settings-popup"
      className="bg-theme-panel"
      style={{
        position: "fixed",
        left: anchor.left,
        bottom: anchor.bottom,
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 6,
        zIndex: 1300,
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
        minWidth: 180,
        overflow: "hidden",
      }}
      onMouseDown={(e) => e.stopPropagation()}
    >
      {/* New Prompt */}
      <button
        type="button"
        onClick={onNewPrompt}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "8px 12px",
          border: "none",
          background: "transparent",
          color: "var(--theme-text)",
          cursor: "pointer",
          fontSize: "0.8rem",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background =
            "rgba(255,255,255,0.06)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background =
            "transparent";
        }}
      >
        <LucideIcon name="message-square-plus" size={14} />
        <span>New Prompt</span>
      </button>

      {/* Save Prompt */}
      <button
        type="button"
        onClick={onSavePrompt}
        disabled={saving || promptEmpty}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "8px 12px",
          border: "none",
          background: "transparent",
          color: "var(--theme-text)",
          cursor:
            saving || promptEmpty ? "default" : "pointer",
          fontSize: "0.8rem",
          opacity: saving || promptEmpty ? 0.4 : 1,
        }}
        onMouseEnter={(e) => {
          if (!(saving || promptEmpty))
            (e.currentTarget as HTMLButtonElement).style.background =
              "rgba(255,255,255,0.06)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background =
            "transparent";
        }}
      >
        <LucideIcon name={saving ? "loader" : "save"} size={14} />
        <span>Save Prompt</span>
      </button>

      {/* Load saved prompts */}
      <button
        type="button"
        onClick={onLoadSavedPrompts}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "8px 12px",
          border: "none",
          background: "transparent",
          color: "var(--theme-text)",
          cursor: "pointer",
          fontSize: "0.8rem",
          borderTop: "1px solid rgba(255,255,255,0.08)",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background =
            "rgba(255,255,255,0.06)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background =
            "transparent";
        }}
      >
        <LucideIcon name="folder-open" size={14} />
        <span>Load saved prompts</span>
      </button>
    </div>,
    document.body,
  );
}
