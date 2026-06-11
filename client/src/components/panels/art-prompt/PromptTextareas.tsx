import { useState, useRef, useEffect } from "react";
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

const COLLAPSED_STYLE: React.CSSProperties = {
  height: 22, overflow: "hidden", whiteSpace: "nowrap",
  textOverflow: "ellipsis",
  background: "transparent", color: "var(--theme-text)",
  border: "none", outline: "none",
  padding: "0 10px 8px", fontFamily: "inherit", fontSize: "inherit",
  opacity: 0.5, cursor: "text",
};

type FieldKey = "prompt" | "secondaryPrompt" | "negativePrompt" | "secondaryNegativePrompt";

export function PromptTextareas({
  prompt, secondaryPrompt, negativePrompt, secondaryNegativePrompt,
  isMultiPrompt, generating,
  onPromptChange, onSecondaryPromptChange, onNegativePromptChange, onSecondaryNegativePromptChange,
}: Props) {
  const [activeField, setActiveField] = useState<FieldKey | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (activeField && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [activeField]);

  const fields: { key: FieldKey; label: string; placeholder: string; value: string; onChange: (v: string) => void }[] = [
    { key: "prompt", label: isMultiPrompt ? "Prompt 1" : "Prompt", placeholder: "Describe the image…", value: prompt, onChange: onPromptChange },
  ];
  if (isMultiPrompt) {
    fields.push(
      { key: "secondaryPrompt", label: "Prompt 2", placeholder: "Background, colors, atmosphere…", value: secondaryPrompt, onChange: onSecondaryPromptChange },
      { key: "negativePrompt", label: "Negative Prompt", placeholder: "Things to exclude…", value: negativePrompt, onChange: onNegativePromptChange },
      { key: "secondaryNegativePrompt", label: "Negative Prompt 2", placeholder: "Secondary negative…", value: secondaryNegativePrompt, onChange: onSecondaryNegativePromptChange },
    );
  }

  return (
    <div className="scroll-panel d-flex flex-column">
      {fields.map((f) => {
        const isActive = activeField === f.key;
        return (
          <div key={f.key} className="d-flex flex-column" style={{ flex: isActive ? 1 : "0 0 auto" }}>
            <PromptDivider label={f.label} />
            {isActive ? (
              <textarea
                ref={textareaRef}
                style={TEXTAREA_STYLE}
                value={f.value}
                onChange={(e) => f.onChange(e.target.value)}
                placeholder={f.placeholder}
                disabled={generating}
              />
            ) : (
              <div
                style={COLLAPSED_STYLE}
                onClick={() => setActiveField(f.key)}
              >
                {f.value || f.placeholder}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
