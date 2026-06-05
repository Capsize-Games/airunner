import { useState, useEffect, useCallback } from "react";
import PromptInput from "./art-prompt/PromptInput";
import { EmbeddingPills, LoraPills } from "./art-prompt/ActivePills";
import ArtPromptFooter from "./art-prompt/ArtPromptFooter";
import { useArtGeneration } from "./art-prompt/useArtGeneration";
import {
  loadPromptData,
  savePromptData,
} from "./art-prompt/ArtPromptStorage";
import LucideIcon from "../shared/LucideIcon";

interface ArtPromptPanelProps {
  showArtModelSettings: boolean;
  onToggleArtModelSettings: () => void;
}

export default function ArtPromptPanel({
  showArtModelSettings,
  onToggleArtModelSettings,
}: ArtPromptPanelProps) {
  const initial = loadPromptData();

  const [prompt, setPrompt] = useState(initial.prompt);
  const [negativePrompt, setNegativePrompt] = useState(
    initial.negative_prompt,
  );
  const [secondaryPrompt, setSecondaryPrompt] = useState(
    initial.secondary_prompt,
  );
  const [secondaryNegativePrompt, setSecondaryNegativePrompt] = useState(
    initial.secondary_negative_prompt,
  );
  const [activeLoras, setActiveLoras] = useState<
    { id: number; name: string }[]
  >([]);
  const [activeEmbeddings, setActiveEmbeddings] = useState<
    { id: number; name: string }[]
  >([]);

  const {
    generating,
    progress,
    handleSubmit,
    handleCancel,
  } = useArtGeneration();

  const reloadActiveLoras = useCallback(async () => {
    try {
      const { listLoras } = await import("../../api/client");
      const data = await listLoras();
      const enabled = (data.loras ?? [])
        .filter((l) => l.enabled)
        .map((l) => ({ id: l.id, name: l.name }));
      setActiveLoras(enabled);
    } catch { /* */ }
  }, []);

  const reloadActiveEmbeddings = useCallback(async () => {
    try {
      const { listEmbeddings } = await import("../../api/client");
      const data = await listEmbeddings();
      const enabled = (data.embeddings ?? [])
        .filter((e) => e.enabled)
        .map((e) => ({ id: e.id, name: e.name }));
      setActiveEmbeddings(enabled);
    } catch { /* */ }
  }, []);

  useEffect(() => {
    reloadActiveLoras();
    const handler = () => reloadActiveLoras();
    window.addEventListener("lora-changed", handler);
    return () => window.removeEventListener("lora-changed", handler);
  }, [reloadActiveLoras]);

  const [versionBump, setVersionBump] = useState(0);

  useEffect(() => {
    const handler = () => setVersionBump((v) => v + 1);
    window.addEventListener("art-version-changed", handler);
    return () => window.removeEventListener("art-version-changed", handler);
  }, []);

  useEffect(() => {
    reloadActiveEmbeddings();
    const handler = () => reloadActiveEmbeddings();
    window.addEventListener("embedding-changed", handler);
    return () => window.removeEventListener("embedding-changed", handler);
  }, [reloadActiveEmbeddings]);

  const persist = (updates: Record<string, string>) => {
    const current = loadPromptData();
    savePromptData({ ...current, ...updates });
  };

  const readLs = (key: string) => {
    try { return localStorage.getItem(key) || ""; } catch { return ""; }
  };

  const onSubmit = () => {
    handleSubmit({
      prompt,
      negativePrompt,
      artModel: readLs("airunner_art_model"),
      artVersion: readLs("airunner_art_version"),
      scheduler: readLs("airunner_art_scheduler"),
    });
  };

  const deactivateLora = (id: number) => {
    import("../../api/client").then(({ updateLora }) => {
      updateLora(id, { enabled: false })
        .then(() => {
          setActiveLoras((prev) => prev.filter((l) => l.id !== id));
          window.dispatchEvent(
            new CustomEvent("lora-changed", { detail: { id, enabled: false } }),
          );
        })
        .catch(() => {});
    });
  };

  const deactivateEmbedding = (id: number) => {
    import("../../api/client").then(({ updateEmbedding }) => {
      updateEmbedding(id, { enabled: false })
        .then(() => {
          setActiveEmbeddings((prev) => prev.filter((e) => e.id !== id));
          window.dispatchEvent(
            new CustomEvent("embedding-changed", { detail: { id, enabled: false } }),
          );
        })
        .catch(() => {});
    });
  };

  return (
    <div className="d-flex flex-column h-100 p-2">
      <div className="d-flex align-items-center gap-2 mb-2 flex-shrink-0">
        <h6 style={{ color: "var(--theme-text-secondary)" }} className="mb-0 flex-grow-1">
          Art Prompt
        </h6>
        <button
          type="button"
          onClick={onToggleArtModelSettings}
          title={showArtModelSettings ? "Hide model settings" : "Show model settings"}
          style={{
            background: showArtModelSettings
              ? "rgba(99,153,255,0.2)"
              : "transparent",
            border: "1px solid #444",
            borderRadius: 4,
            width: 26,
            height: 26,
            padding: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          <LucideIcon name="settings" size={14} />
        </button>
      </div>

      <div className="flex-grow-1 d-flex flex-column gap-2 overflow-auto">
        <PromptInput
          label="Prompt"
          value={prompt}
          onChange={(v) => { setPrompt(v); persist({ prompt: v }); }}
          placeholder="Describe the image..."
          disabled={generating}
        />

        {readLs("airunner_art_version") !== "Z-Image Turbo" && (
          <>
            <PromptInput
              label="Secondary Prompt"
              value={secondaryPrompt}
              onChange={(v) => { setSecondaryPrompt(v); persist({ secondary_prompt: v }); }}
              placeholder="Background, colors, atmosphere..."
              disabled={generating}
            />

            <PromptInput
              label="Negative Prompt"
              value={negativePrompt}
              onChange={(v) => { setNegativePrompt(v); persist({ negative_prompt: v }); }}
              placeholder="Things to exclude..."
              disabled={generating}
            />

            <PromptInput
              label="Sec. Negative"
              value={secondaryNegativePrompt}
              onChange={(v) => {
                setSecondaryNegativePrompt(v);
                persist({ secondary_negative_prompt: v });
              }}
              placeholder="Secondary negative..."
              disabled={generating}
            />
          </>
        )}
      </div>

      <div className="flex-shrink-0 mt-2">
        <EmbeddingPills
          embeddings={activeEmbeddings}
          onDeactivate={deactivateEmbedding}
        />
        <LoraPills
          loras={activeLoras}
          onDeactivate={deactivateLora}
        />
        <ArtPromptFooter
          progress={progress}
          generating={generating}
          hasPrompt={!!prompt.trim()}
          onSubmit={onSubmit}
          onCancel={handleCancel}
        />
      </div>
    </div>
  );
}
