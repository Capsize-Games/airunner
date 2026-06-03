import { useState, useEffect, useRef, useCallback } from "react";
import {
  startArtGeneration,
  getArtJobStatus,
} from "../../api/client";
import ProgressBar from "react-bootstrap/ProgressBar";
import PromptInput from "./art-prompt/PromptInput";
import { EmbeddingPills, LoraPills } from "./art-prompt/ActivePills";
import ArtPromptFooter from "./art-prompt/ArtPromptFooter";

const STORAGE_KEY = "airunner_art_prompt_data";

interface PromptData {
  prompt: string;
  negative_prompt: string;
  secondary_prompt: string;
  secondary_negative_prompt: string;
}

const DEFAULT_PROMPT_DATA: PromptData = {
  prompt: "",
  negative_prompt: "",
  secondary_prompt: "",
  secondary_negative_prompt: "",
};

function loadPromptData(): PromptData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as PromptData;
  } catch { /* ignore */ }
  return { ...DEFAULT_PROMPT_DATA };
}

function savePromptData(data: Record<string, string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch { /* ignore */ }
}

export default function ArtPromptPanel() {
  const initial = loadPromptData();
  const savedVersion = (() => {
    try { return localStorage.getItem("airunner_art_version") || ""; }
    catch { return ""; }
  })();

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
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const jobIdRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [artVersion, setArtVersion] = useState(savedVersion);
  const [artModel, setArtModel] = useState(() => {
    try { return localStorage.getItem("airunner_art_model") || ""; }
    catch { return ""; }
  });
  const [isZImage, setIsZImage] = useState(
    savedVersion === "Z-Image Turbo",
  );
  const [activeLoras, setActiveLoras] = useState<
    { id: number; name: string }[]
  >([]);
  const [activeEmbeddings, setActiveEmbeddings] = useState<
    { id: number; name: string }[]
  >([]);

  const reloadActiveLoras = useCallback(async () => {
    try {
      const { listLoras } = await import("../../api/client");
      const data = await listLoras();
      const version = (() => {
        try {
          return localStorage.getItem("airunner_art_version") || "";
        } catch { return ""; }
      })();
      const enabled = (data.loras ?? [])
        .filter((l) => l.enabled)
        .filter((l) =>
          version ? l.path.includes(`/${version}/`) : true,
        )
        .map((l) => ({ id: l.id, name: l.name }));
      setActiveLoras(enabled);
    } catch { /* */ }
  }, []);

  const reloadActiveEmbeddings = useCallback(async () => {
    try {
      const { listEmbeddings } = await import("../../api/client");
      const data = await listEmbeddings();
      const version = (() => {
        try {
          return localStorage.getItem("airunner_art_version") || "";
        } catch { return ""; }
      })();
      const enabled = (data.embeddings ?? [])
        .filter((e) => e.enabled)
        .filter((e) =>
          version ? e.path.includes(`/${version}/`) : true,
        )
        .map((e) => ({ id: e.id, name: e.name }));
      setActiveEmbeddings(enabled);
    } catch { /* */ }
  }, []);

  useEffect(() => {
    const versionHandler = (e: Event) => {
      const v = (e as CustomEvent).detail as string;
      setArtVersion(v);
      setIsZImage(v === "Z-Image Turbo");
      reloadActiveLoras();
      reloadActiveEmbeddings();
    };
    const modelHandler = (e: Event) => {
      const m = (e as CustomEvent).detail as string;
      setArtModel(m ?? "");
    };
    window.addEventListener("art-version-changed", versionHandler);
    window.addEventListener("art-model-changed", modelHandler);
    try {
      const m = localStorage.getItem("airunner_art_model");
      if (m) setArtModel(m);
    } catch {}
    return () => {
      window.removeEventListener("art-version-changed", versionHandler);
      window.removeEventListener("art-model-changed", modelHandler);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [reloadActiveLoras, reloadActiveEmbeddings]);

  useEffect(() => {
    reloadActiveLoras();
    const handler = () => reloadActiveLoras();
    window.addEventListener("lora-changed", handler);
    return () => window.removeEventListener("lora-changed", handler);
  }, [reloadActiveLoras]);

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

  const handleSubmit = async () => {
    if (generating || !prompt.trim()) return;
    setGenerating(true);
    setProgress(0);
    try {
      const scheduler = (() => {
        try { return localStorage.getItem("airunner_art_scheduler") || ""; }
        catch { return ""; }
      })();
      const resp = await startArtGeneration({
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || undefined,
        model: artModel || undefined,
        version: artVersion || undefined,
        scheduler: scheduler || undefined,
        num_images: 1,
      });
      jobIdRef.current = resp.job_id;
      pollRef.current = setInterval(async () => {
        try {
          const status = await getArtJobStatus(resp.job_id);
          setProgress(status.progress ?? 0);
          if (
            status.status === "complete" ||
            status.status === "failed"
          ) {
            handleCancel();
          }
        } catch {
          // keep polling
        }
      }, 1000);
    } catch {
      setGenerating(false);
    }
  };

  const handleCancel = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    jobIdRef.current = null;
    setGenerating(false);
    setProgress(0);
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
      <h6 style={{ color: "var(--theme-text-secondary)" }}
        className="mb-2 flex-shrink-0"
      >
        Art Prompt
      </h6>

      <div className="flex-grow-1 d-flex flex-column gap-2 overflow-hidden">
        <PromptInput
          label="Prompt"
          value={prompt}
          onChange={(v) => { setPrompt(v); persist({ prompt: v }); }}
          placeholder="Describe the image..."
          disabled={generating}
        />

        {!isZImage && (
          <PromptInput
            label="Secondary Prompt"
            value={secondaryPrompt}
            onChange={(v) => { setSecondaryPrompt(v); persist({ secondary_prompt: v }); }}
            placeholder="Background, colors, atmosphere..."
            disabled={generating}
          />
        )}

        {!isZImage && (
          <PromptInput
            label="Negative Prompt"
            value={negativePrompt}
            onChange={(v) => { setNegativePrompt(v); persist({ negative_prompt: v }); }}
            placeholder="Things to exclude..."
            disabled={generating}
          />
        )}

        {!isZImage && (
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
          artVersion={artVersion}
          artModel={artModel}
          onVersionChange={(v) => {
            setArtVersion(v);
            setArtModel("");
            setIsZImage(v === "Z-Image Turbo");
          }}
          onModelChange={(m) => setArtModel(m)}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
        />
      </div>
    </div>
  );
}
