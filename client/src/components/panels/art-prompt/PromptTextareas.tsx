import { PromptDivider } from "./ArtShared";

interface Props {
  prompt: string;
  secondaryPrompt: string;
  negativePrompt: string;
  secondaryNegativePrompt: string;
  isMultiPrompt: boolean;
  generating: boolean;
  onPromptChange: (v: string) => void;
  onSecondaryPromptChange: (v: string) => void;
  onNegativePromptChange: (v: string) => void;
  onSecondaryNegativePromptChange: (v: string) => void;
}

const TEXTAREA_STYLE: React.CSSProperties = {
  resize: "none", flex: 1,
  background: "transparent", color: "var(--theme-text)",
  border: "none", outline: "none",
  padding: "8px 10px", fontFamily: "inherit", fontSize: "inherit",
};

export function PromptTextareas({
  prompt, secondaryPrompt, negativePrompt, secondaryNegativePrompt,
  isMultiPrompt, generating,
  onPromptChange, onSecondaryPromptChange, onNegativePromptChange, onSecondaryNegativePromptChange,
}: Props) {
  return (
    <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", minHeight: 0 }}>
      <textarea
        style={TEXTAREA_STYLE}
        value={prompt}
        onChange={(e) => onPromptChange(e.target.value)}
        placeholder="Describe the image…"
        disabled={generating}
      />
      {isMultiPrompt && (
        <>
          <PromptDivider label="Prompt 2" />
          <textarea
            style={TEXTAREA_STYLE}
            value={secondaryPrompt}
            onChange={(e) => onSecondaryPromptChange(e.target.value)}
            placeholder="Background, colors, atmosphere…"
            disabled={generating}
          />
          <PromptDivider label="Negative Prompt" />
          <textarea
            style={TEXTAREA_STYLE}
            value={negativePrompt}
            onChange={(e) => onNegativePromptChange(e.target.value)}
            placeholder="Things to exclude…"
            disabled={generating}
          />
          <PromptDivider label="Negative Prompt 2" />
          <textarea
            style={TEXTAREA_STYLE}
            value={secondaryNegativePrompt}
            onChange={(e) => onSecondaryNegativePromptChange(e.target.value)}
            placeholder="Secondary negative…"
            disabled={generating}
          />
        </>
      )}
    </div>
  );
}
