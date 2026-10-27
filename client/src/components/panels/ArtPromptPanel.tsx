import {
  useState, useEffect, useCallback, useRef,
} from "react";
import { updateSingleton } from "../../api/client";
import ArtPromptToolbar from "./art-prompt/ArtPromptToolbar";
import ArtModelSliders from "./art-model/ArtModelSliders";
import { saveToStorage, loadFromStorage } from "./art-model/ArtModelStorage";
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

const ART_PANEL_W = 260;
const LS_COLLAPSED = "canvas_art_panel_collapsed";

const TABS: { id: ArtTab; label: string; icon: string }[] = [
  { id: "prompt", label: "Prompt", icon: "message-square-heart" },
  { id: "lora", label: "LoRA", icon: "puzzle" },
  { id: "embeddings", label: "Embeddings", icon: "scan-text" },
];

const railBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  cursor: "pointer",
  color: "rgba(255,255,255,0.4)",
  padding: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  borderRadius: 4,
  width: 28,
  height: 28,
  flexShrink: 0,
};

export default function ArtPromptPanel() {
  const initial = loadPromptData();

  const [tab, setTab] = useState<ArtTab>("prompt");
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_COLLAPSED) === "true"; } catch { return false; }
  });
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

  // Output size state
  const [genWidth, setGenWidth] = useState(512);
  const [genHeight, setGenHeight] = useState(512);

  // Generation parameter state (samples, batch, steps, cfg)
  const [nSamples, setNSamples] = useState(() => loadFromStorage("n_samples", 1));
  const [imagesPerBatch, setImagesPerBatch] = useState(() => loadFromStorage("images_per_batch", 1));
  const [steps, setSteps] = useState(() => loadFromStorage("steps", 20));
  const [cfgScale, setCfgScale] = useState(() => loadFromStorage("cfg_scale", 7.5));

  const persistGen = (updates: Record<string, unknown>) => {
    updateSingleton("GeneratorSettings", updates).catch(() => {});
  };

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
        width: genWidth,
        height: genHeight,
      });
      setPhase("completed");
      if (imageBase64 && canvasCtx) {
        const docW = canvasCtx.documentWidth ?? genWidth;
        const docH = canvasCtx.documentHeight ?? genHeight;
        canvasCtx.placeImageOnNewLayer(
          imageBase64,
          Math.round((docW - genWidth) / 2),
          Math.round((docH - genHeight) / 2),
          genWidth,
          genHeight,
        );
      }
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : String(err);
      setPhase(msg === "Cancelled" ? "cancelled" : "failed");
    }
  }, [prompt, negativePrompt, genWidth, genHeight, canvasCtx, artGenerate]);

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

  const collapseToStorage = (val: boolean) => {
    setCollapsed(val);
    try { localStorage.setItem(LS_COLLAPSED, String(val)); } catch { /* */ }
  };

  if (collapsed) {
    return (
      <div
        style={{
          width: 32,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          background: "var(--theme-panel-bg)",
          borderRight: "1px solid var(--separator-color)",
          padding: "4px 0",
          gap: 2,
          overflow: "hidden",
        }}
      >
        <button
          style={railBtnStyle}
          title="Expand art panel"
          onClick={() => collapseToStorage(false)}
        >
          <LucideIcon name="chevron-right" size={14} />
        </button>
        <div style={{ width: "60%", height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />
        {TABS.map((t) => (
          <button
            key={t.id}
            style={{
              ...railBtnStyle,
              color: tab === t.id ? "var(--bs-primary)" : "rgba(255,255,255,0.4)",
            }}
            title={t.label}
            onClick={() => { setTab(t.id); collapseToStorage(false); }}
          >
            <LucideIcon name={t.icon} size={14} />
          </button>
        ))}
      </div>
    );
  }

  return (
    <div
      style={{
        width: ART_PANEL_W,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        borderRight: "1px solid var(--separator-color)",
      }}
    >
      {/* Collapse header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexShrink: 0,
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          padding: "2px 4px",
        }}
      >
        <button
          type="button"
          onClick={() => collapseToStorage(true)}
          title="Collapse art panel"
          style={{ ...railBtnStyle, width: 24, height: 24, color: "rgba(255,255,255,0.25)", flexShrink: 0 }}
        >
          <LucideIcon name="chevron-left" size={13} />
        </button>
        <span style={{ fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.25)", letterSpacing: "0.06em", paddingLeft: 4 }}>ART PROMPT</span>
      </div>

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
              background: tab === t.id ? "var(--theme-panel-bg)" : "transparent",
              border: "none",
              borderBottom: tab === t.id ? "2px solid var(--bs-primary)" : "2px solid transparent",
              color: tab === t.id ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
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
        <div className="d-flex flex-column flex-grow-1 overflow-hidden">
          <div className="flex-grow-1 d-flex flex-column gap-2 overflow-auto p-2">
            {(() => {
              const isMultiPrompt = readLs("airunner_art_version") !== "Z-Image Turbo";
              return (
                <>
                  <PromptInput
                    label={isMultiPrompt ? "Prompt 1" : "Prompt"}
                    value={prompt}
                    onChange={(v) => { setPrompt(v); persist({ prompt: v }); }}
                    placeholder="Describe the image..."
                    disabled={generating}
                  />
                  {isMultiPrompt && (
                    <>
                      <PromptInput
                        label="Prompt 2"
                        value={secondaryPrompt}
                        onChange={(v) => { setSecondaryPrompt(v); persist({ secondary_prompt: v }); }}
                        placeholder="Background, colors, atmosphere..."
                        disabled={generating}
                      />
                      <PromptInput
                        label="Negative Prompt 1"
                        value={negativePrompt}
                        onChange={(v) => { setNegativePrompt(v); persist({ negative_prompt: v }); }}
                        placeholder="Things to exclude..."
                        disabled={generating}
                      />
                      <PromptInput
                        label="Negative Prompt 2"
                        value={secondaryNegativePrompt}
                        onChange={(v) => { setSecondaryNegativePrompt(v); persist({ secondary_negative_prompt: v }); }}
                        placeholder="Secondary negative..."
                        disabled={generating}
                      />
                    </>
                  )}
                </>
              );
            })()}
          </div>

          <div className="flex-shrink-0" style={{ padding: "0 8px 8px" }}>
            <EmbeddingPills embeddings={activeEmbeddings} onDeactivate={deactivateEmbedding} />
            <LoraPills loras={activeLoras} onDeactivate={deactivateLora} />
            {/* Model / version / scheduler — above generation sliders */}
            <ArtPromptToolbar />
            <ArtModelSliders
              nSamples={nSamples}
              imagesPerBatch={imagesPerBatch}
              steps={steps}
              cfgScale={cfgScale}
              onNSamplesChange={(v) => { setNSamples(v); saveToStorage("n_samples", v); persistGen({ n_samples: v }); }}
              onImagesPerBatchChange={(v) => { setImagesPerBatch(v); saveToStorage("images_per_batch", v); persistGen({ images_per_batch: v }); }}
              onStepsChange={(v) => { setSteps(v); saveToStorage("steps", v); persistGen({ steps: v }); }}
              onCfgScaleChange={(v) => { setCfgScale(v); saveToStorage("cfg_scale", v); persistGen({ cfg_scale: v }); }}
            />
            <div style={{ marginTop: 8 }} />
            <SeedControls
              seed={seed}
              seedRandomized={seedRandomized}
              loading={false}
              onSeedChange={handleSeedChange}
              onToggleRandom={handleToggleRandom}
            />
            {/* Output W × H */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", flexShrink: 0 }}>W</span>
              <input
                type="number" min={64} max={2048} step={64} value={genWidth}
                onChange={(e) => setGenWidth(Math.max(64, Math.min(2048, Number(e.target.value))))}
                style={{ flex: 1, minWidth: 0, background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "rgba(255,255,255,0.8)", fontSize: 11, textAlign: "center", padding: "3px 2px" }}
              />
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", flexShrink: 0 }}>H</span>
              <input
                type="number" min={64} max={2048} step={64} value={genHeight}
                onChange={(e) => setGenHeight(Math.max(64, Math.min(2048, Number(e.target.value))))}
                style={{ flex: 1, minWidth: 0, background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "rgba(255,255,255,0.8)", fontSize: 11, textAlign: "center", padding: "3px 2px" }}
              />
            </div>
            {phase !== "idle" && <StatusBadge phase={phase} progress={progress} />}
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
