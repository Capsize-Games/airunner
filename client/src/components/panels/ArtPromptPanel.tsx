import {
  useState, useEffect, useCallback, useRef,
} from "react";
import { updateSingleton } from "../../api/client";
import PromptInput from "./art-prompt/PromptInput";
import { EmbeddingPills, LoraPills } from "./art-prompt/ActivePills";
import ArtPromptFooter from "./art-prompt/ArtPromptFooter";
import SeedControls from "./art-model/SeedControls";
import LoraPanel from "./LoraPanel";
import EmbeddingsPanel from "./EmbeddingsPanel";
import {
  loadPromptData,
  savePromptData,
} from "./art-prompt/ArtPromptStorage";
import LucideIcon from "../shared/LucideIcon";
import { useCanvasContext } from "../../features/canvas/CanvasContext";
import { useArtWebSocket } from "../../features/art/useArtWebSocket";

type ArtTab = "prompt" | "lora" | "embeddings";

const TABS: { id: ArtTab; label: string; icon: string }[] = [
  { id: "prompt", label: "Prompt", icon: "pencil" },
  { id: "lora", label: "LoRA", icon: "puzzle" },
  { id: "embeddings", label: "Embeddings", icon: "scan-text" },
];

export default function ArtPromptPanel() {
  const initial = loadPromptData();

  const [tab, setTab] = useState<ArtTab>("prompt");
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

  // Seed state (persisted to localStorage and server)
  const [seed, setSeed] = useState(() => {
    try {
      const v = Number(localStorage.getItem("airunner_seed") || "0");
      return v === -1 ? Math.floor(Math.random() * 2147483647) + 1 : v;
    } catch { return 0; }
  });
  const [seedRandomized, setSeedRandomized] = useState(() => {
    try { return Number(localStorage.getItem("airunner_seed") || "0") === -1; }
    catch { return false; }
  });

  // Canvas context for grid dimensions and image placement
  let canvasCtx: ReturnType<typeof useCanvasContext> | null = null;
  try {
    canvasCtx = useCanvasContext();
  } catch {
    // not inside a canvas provider
  }

  const activeGridArea = canvasCtx?.activeGridArea ?? {
    x: 0, y: 0, width: 512, height: 512,
  };

  const {
    generating,
    progress,
    generate: artGenerate,
    cancel: artCancel,
  } = useArtWebSocket();

  type Phase =
    | "idle" | "loading"
    | "completed" | "cancelled" | "failed";

  const [phase, setPhase] = useState<Phase>("idle");
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-dismiss status messages after a few seconds
  useEffect(() => {
    if (
      phase === "completed" ||
      phase === "cancelled" ||
      phase === "failed"
    ) {
      if (hideTimer.current) clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => {
        setPhase("idle");
      }, 4000);
    }
    return () => {
      if (hideTimer.current) clearTimeout(hideTimer.current);
    };
  }, [phase]);

  const onGenerate = useCallback(async () => {
    if (!prompt.trim()) return;
    setPhase("loading");
    const ls = (k: string) => {
      try { return localStorage.getItem(k) || ""; } catch { return ""; }
    };
    const lsNum = (k: string): number | undefined => {
      try {
        const v = localStorage.getItem(k);
        if (v === null || v === "") return undefined;
        const n = Number(v);
        return isNaN(n) ? undefined : n;
      } catch { return undefined; }
    };
    try {
      const imageBase64 = await artGenerate({
        prompt: prompt.trim(),
        negativePrompt: negativePrompt?.trim() || undefined,
        seed: lsNum("airunner_seed"),
        artModel: ls("airunner_art_model") || undefined,
        artVersion: ls("airunner_art_version") || undefined,
        scheduler: ls("airunner_art_scheduler") || undefined,
        width: activeGridArea.width,
        height: activeGridArea.height,
      });
      setPhase("completed");
      if (imageBase64 && canvasCtx) {
        canvasCtx.placeImageOnNewLayer(
          imageBase64,
          activeGridArea.x,
          activeGridArea.y,
          activeGridArea.width,
          activeGridArea.height,
        );
      }
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : String(err);
      setPhase(msg === "Cancelled" ? "cancelled" : "failed");
    }
  }, [prompt, negativePrompt, activeGridArea, canvasCtx, artGenerate]);

  const onCancel = useCallback(() => {
    artCancel();
  }, [artCancel]);

  const handleSeedChange = useCallback((v: number) => {
    setSeed(v);
    setSeedRandomized(false);
    try { localStorage.setItem("airunner_seed", String(v)); } catch {}
    updateSingleton("GeneratorSettings", { seed: v }).catch(() => {});
  }, []);

  const handleToggleRandom = useCallback(() => {
    if (seedRandomized) {
      setSeedRandomized(false);
      try { localStorage.setItem("airunner_seed", String(seed)); } catch {}
      updateSingleton("GeneratorSettings", { seed }).catch(() => {});
    } else {
      const s = Math.floor(Math.random() * 2147483647) + 1;
      setSeedRandomized(true);
      setSeed(s);
      try { localStorage.setItem("airunner_seed", String(-1)); } catch {}
      updateSingleton("GeneratorSettings", { seed: -1 }).catch(() => {});
    }
  }, [seed, seedRandomized]);

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

  const [, setVersionBump] = useState(0);

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
    <div className="d-flex flex-column h-100">
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          flexShrink: 0,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            style={{
              flex: 1,
              padding: "6px 4px",
              background: tab === t.id
                ? "var(--theme-panel-bg)"
                : "transparent",
              border: "none",
              borderBottom: tab === t.id
                ? "2px solid var(--bs-primary)"
                : "2px solid transparent",
              color: tab === t.id
                ? "var(--bs-primary)"
                : "rgba(255,255,255,0.45)",
              fontSize: 11,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 4,
              transition: "color 0.15s, border-color 0.15s",
            }}
          >
            <LucideIcon name={t.icon} size={12} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "prompt" && (
        <div className="d-flex flex-column flex-grow-1 overflow-hidden p-2">
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
                  label="Secondary Negative Prompt"
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
            <SeedControls
              seed={seed}
              seedRandomized={seedRandomized}
              loading={false}
              onSeedChange={handleSeedChange}
              onToggleRandom={handleToggleRandom}
            />
            {phase !== "idle" && (
              <StatusBadge phase={phase} progress={progress} />
            )}
            <ArtPromptFooter
              progress={progress}
              generating={generating}
              hasPrompt={!!prompt.trim()}
              onSubmit={onGenerate}
              onCancel={onCancel}
            />
          </div>
        </div>
      )}

      {tab === "lora" && (
        <div className="flex-grow-1 overflow-auto">
          <LoraPanel />
        </div>
      )}

      {tab === "embeddings" && (
        <div className="flex-grow-1 overflow-auto">
          <EmbeddingsPanel />
        </div>
      )}
    </div>
  );
}

/* ── Inline status badge component ── */

const STATUS_CFG: Record<
  string,
  { icon: string; label: string; bg: string; border: string; color: string }
> = {
  loading: {
    icon: "sparkles",
    label: "Loading model\u2026",
    bg: "rgba(99,153,255,0.12)",
    border: "rgba(99,153,255,0.25)",
    color: "#6399ff",
  },
  completed: {
    icon: "circle-check",
    label: "Image generated",
    bg: "rgba(40,167,69,0.15)",
    border: "rgba(40,167,69,0.3)",
    color: "#28a745",
  },
  cancelled: {
    icon: "circle-x",
    label: "Cancelled generation",
    bg: "rgba(255,193,7,0.15)",
    border: "rgba(255,193,7,0.3)",
    color: "#ffc107",
  },
  failed: {
    icon: "circle-x",
    label: "Failed generation",
    bg: "rgba(220,53,69,0.15)",
    border: "rgba(220,53,69,0.3)",
    color: "#dc3545",
  },
};

function StatusBadge({
  phase,
  progress,
}: {
  phase: string;
  progress: number;
}) {
  const cfg = STATUS_CFG[phase];
  if (!cfg) return null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        marginBottom: 6,
        padding: "4px 8px",
        borderRadius: 4,
        background: cfg.bg,
        border: `1px solid ${cfg.border}`,
        color: cfg.color,
        fontSize: 12,
        lineHeight: 1.4,
      }}
    >
      <LucideIcon name={cfg.icon} size={14} />
      <span>{cfg.label}</span>
    </div>
  );
}
