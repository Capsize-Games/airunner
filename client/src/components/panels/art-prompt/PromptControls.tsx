import LucideIcon from "../../shared/LucideIcon";
import { ToolbarIconBtn } from "./ArtShared";

type Phase = "idle" | "loading" | "completed" | "cancelled" | "failed";

interface Props {
  generating: boolean;
  progress: number;
  phase: Phase;
  hasPrompt: boolean;
  saving: boolean;
  onClear: () => void;
  onSave: () => void;
  onToggleSavedPrompts: () => void;
  onGenerate: () => void;
  onCancel: () => void;
}

function generateBg(phase: Phase, hasPrompt: boolean): string {
  if (phase === "completed") return "var(--bs-success)";
  if (phase === "failed" || phase === "cancelled") return "var(--bs-danger)";
  return hasPrompt ? "var(--bs-primary)" : "rgba(255,255,255,0.1)";
}

export function PromptControls({
  generating, progress, phase, hasPrompt, saving,
  onClear, onSave, onToggleSavedPrompts, onGenerate, onCancel,
}: Props) {
  return (
    <div style={{
      borderTop: "1px solid rgba(255,255,255,0.08)",
      padding: "4px 6px 5px",
      display: "flex", alignItems: "center", gap: 2,
      flexShrink: 0,
    }}>
      {/* Left: new / save / load */}
      <ToolbarIconBtn title="New prompt" onClick={onClear}>
        <LucideIcon name="plus" size={15} />
      </ToolbarIconBtn>
      <ToolbarIconBtn title="Save prompt" onClick={onSave} disabled={saving || !hasPrompt}>
        <LucideIcon name={saving ? "loader" : "save"} size={14} />
      </ToolbarIconBtn>
      <ToolbarIconBtn title="Load saved prompts" onClick={onToggleSavedPrompts}>
        <LucideIcon name="folder-open" size={14} />
      </ToolbarIconBtn>

      <span style={{ flex: 1 }} />

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
}
