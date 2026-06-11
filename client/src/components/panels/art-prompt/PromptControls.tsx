import { forwardRef, type RefObject } from "react";
import LucideIcon from "../../shared/LucideIcon";
import { ToolbarIconBtn } from "./ArtShared";

type Phase = "idle" | "loading" | "completed" | "cancelled" | "failed";

interface Props {
  generating: boolean;
  progress: number;
  phase: Phase;
  hasPrompt: boolean;
  saving: boolean;
  promptPopupOpen: boolean;
  promptBtnRef: RefObject<HTMLDivElement | null>;
  activeLoras: { id: number; name: string }[];
  activeEmbeddings: { id: number; name: string }[];
  isMultiPrompt: boolean;
  loraPanelOpen: boolean;
  embeddingsPanelOpen: boolean;
  seedRandomized: boolean;
  onClear: () => void;
  onSave: () => void;
  onToggleSavedPrompts: () => void;
  onTogglePromptPopup: () => void;
  onToggleLora: () => void;
  onToggleEmbeddings: () => void;
  onToggleRandom: () => void;
  onGenerate: () => void;
  onCancel: () => void;
}

function generateBg(phase: Phase, hasPrompt: boolean): string {
  if (phase === "completed") return "var(--bs-success)";
  if (phase === "failed" || phase === "cancelled") return "var(--bs-danger)";
  return hasPrompt ? "var(--bs-primary)" : "rgba(255,255,255,0.1)";
}

export const PromptControls = forwardRef<HTMLDivElement, Props>(function PromptControls({
  generating, progress, phase, hasPrompt, saving,
  promptPopupOpen, promptBtnRef,
  activeLoras, activeEmbeddings, isMultiPrompt,
  loraPanelOpen, embeddingsPanelOpen, seedRandomized,
  onClear, onSave, onToggleSavedPrompts, onTogglePromptPopup,
  onToggleLora, onToggleEmbeddings, onToggleRandom,
  onGenerate, onCancel,
}, ref) {
  return (
    <div ref={ref} style={{
      borderTop: "1px solid rgba(255,255,255,0.08)",
      padding: "4px 6px 5px",
      display: "flex", alignItems: "center", gap: 2,
      flexShrink: 0,
    }}>
      {/* Left: prompt settings popup trigger */}
      <div ref={promptBtnRef}>
        <ToolbarIconBtn
          title="Prompt settings"
          onClick={onTogglePromptPopup}
          active={promptPopupOpen}
        >
          <LucideIcon name="message-square" size={15} />
        </ToolbarIconBtn>
      </div>

      <span className="flex-grow-1" />

      {/* Right: generate / cancel */}
      {generating ? (
        <button
          type="button" onClick={onCancel}
          title={progress > 0 ? `${progress}% — click to cancel` : "Cancel"}
          style={{
            flexShrink: 0, width: 28, height: 24, padding: 0,
            border: "none", borderRadius: 4, cursor: "pointer",
            background: "var(--bs-danger)", color: "#fff",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          <LucideIcon name="circle-stop" size={13} />
        </button>
      ) : (
        <button
          type="button" onClick={onGenerate} disabled={!hasPrompt}
          title="Generate image"
          style={{
            flexShrink: 0, width: 28, height: 24, padding: 0,
            border: "none", borderRadius: 4,
            cursor: hasPrompt ? "pointer" : "default",
            background: generateBg(phase, hasPrompt),
            color: "#fff",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "background 0.3s",
          }}
        >
          <LucideIcon name="chevron-up" size={13} />
        </button>
      )}
    </div>
  );
});
