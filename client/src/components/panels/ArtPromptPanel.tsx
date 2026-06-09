import {
  useState, useEffect, useCallback, useRef, Fragment,
} from "react";
import { createPortal } from "react-dom";
import { updateSingleton, getArtModelOptions } from "../../api/client";
import type { ArtOptionsResponse } from "../../api/client";
import { createSavedPrompt } from "../../api/art";
import type { SavedPrompt } from "../../api/art";
import { saveToStorage, loadFromStorage } from "./art-model/ArtModelStorage";
import { loadPromptData, savePromptData } from "./art-prompt/ArtPromptStorage";
import SavedPromptsPanel from "./art-prompt/SavedPromptsModal";
import LucideIcon from "../shared/LucideIcon";
import { useCanvasContext } from "../../features/canvas/CanvasContext";
import { useArtWebSocket } from "../../features/art/useArtWebSocket";
import { PromptTextareas } from "./art-prompt/PromptTextareas";
import { PromptToolbar } from "./art-prompt/PromptToolbar";
import { ModelRows } from "./art-prompt/ModelRows";
import { PromptControls } from "./art-prompt/PromptControls";
import { ToolbarIconBtn, type ArtPopup, type ArtPanel } from "./art-prompt/ArtShared";
import { SettingsPopup } from "./art-prompt/SettingsPopup";
import LoraPanel from "./LoraPanel";
import EmbeddingsPanel from "./EmbeddingsPanel";

// side-effect: injects CSS for sliders / number spinners
import "./art-prompt/ArtShared";

const ART_PANEL_DEFAULT = 300;
const ART_PANEL_MIN = 220;
const ART_PANEL_MAX = 520;
const LS_ART_W = "airunner_art_panel_w";
const LS_COLLAPSED = "canvas_art_panel_collapsed";

function saveNum(key: string, val: number) {
  try { localStorage.setItem(key, String(val)); } catch {}
}
function loadNum(key: string, fallback: number): number {
  try { const v = localStorage.getItem(key); return v !== null ? Number(v) : fallback; }
  catch { return fallback; }
}
const ls = (key: string) => {
  try { return localStorage.getItem(key) || ""; } catch { return ""; }
};

let artDragState: { startX: number; startW: number; setW: (w: number) => void } | null = null;

function onArtMouseMove(e: MouseEvent) {
  if (!artDragState) return;
  const delta = e.clientX - artDragState.startX;
  artDragState.setW(Math.max(ART_PANEL_MIN, Math.min(ART_PANEL_MAX, artDragState.startW + delta)));
}
function onArtMouseUp() {
  if (!artDragState) return;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  artDragState = null;
}
if (typeof window !== "undefined") {
  window.addEventListener("mousemove", onArtMouseMove);
  window.addEventListener("mouseup", onArtMouseUp);
}

const railBtnStyle: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  color: "rgba(255,255,255,0.4)", padding: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  borderRadius: 4, width: 28, height: 28, flexShrink: 0,
};

type Phase = "idle" | "loading" | "completed" | "cancelled" | "failed";

export default function ArtPromptPanel() {
  const initial = loadPromptData();

  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_COLLAPSED) === "true"; } catch { return false; }
  });
  const [artW, setArtW] = useState(() => loadNum(LS_ART_W, ART_PANEL_DEFAULT));
  useEffect(() => { saveNum(LS_ART_W, artW); }, [artW]);

  const [prompt, setPrompt] = useState(initial.prompt);
  const [negativePrompt, setNegativePrompt] = useState(initial.negative_prompt);
  const [secondaryPrompt, setSecondaryPrompt] = useState(initial.secondary_prompt);
  const [secondaryNegativePrompt, setSecondaryNegativePrompt] = useState(initial.secondary_negative_prompt);

  const [activeLoras, setActiveLoras] = useState<{ id: number; name: string }[]>([]);
  const [activeEmbeddings, setActiveEmbeddings] = useState<{ id: number; name: string }[]>([]);

  const [artOptions, setArtOptions] = useState<ArtOptionsResponse | null>(null);
  const [version, setVersion] = useState(() => ls("airunner_art_version"));
  const [modelPath, setModelPath] = useState(() => ls("airunner_art_model"));
  const [scheduler, setScheduler] = useState(() => ls("airunner_art_scheduler"));
  const [toolbarLoading, setToolbarLoading] = useState(true);

  const [saving, setSaving] = useState(false);

  const [openPopup, setOpenPopup] = useState<ArtPopup>(null);
  const [openPanel, setOpenPanel] = useState<ArtPanel>(null);
  const [artPanelAnchor, setArtPanelAnchor] = useState<{ left: number; bottom: number; width: number; height: number } | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const settingsBtnRef = useRef<HTMLDivElement>(null);
  const [settingsAnchor, setSettingsAnchor] = useState<{ left: number; bottom: number } | null>(null);
  const emittingRef = useRef(false);

  const availableSchedulers = (artOptions?.versions?.find((v) => v.name === version)?.schedulers) ?? [];

  const [genWidth, setGenWidth] = useState(() => loadFromStorage("gen_width", 512));
  const [genHeight, setGenHeight] = useState(() => loadFromStorage("gen_height", 512));
  const [nSamples, setNSamples] = useState(() => loadFromStorage("n_samples", 1));
  const [imagesPerBatch, setImagesPerBatch] = useState(() => loadFromStorage("images_per_batch", 1));
  const [steps, setSteps] = useState(() => loadFromStorage("steps", 20));
  const [cfgScale, setCfgScale] = useState(() => loadFromStorage("cfg_scale", 7.5));

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

  const [phase, setPhase] = useState<Phase>("idle");
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  let canvasCtx: ReturnType<typeof useCanvasContext> | null = null;
  try { canvasCtx = useCanvasContext(); } catch {}

  const { generating, progress, generate: artGenerate, cancel: artCancel } = useArtWebSocket();

  const isMultiPrompt = ls("airunner_art_version") !== "Z-Image Turbo";
  const [, setVersionBump] = useState(0);

  useEffect(() => {
    const handler = () => setVersionBump((v) => v + 1);
    window.addEventListener("art-version-changed", handler);
    return () => window.removeEventListener("art-version-changed", handler);
  }, []);

  useEffect(() => {
    if (phase === "completed" || phase === "cancelled" || phase === "failed") {
      if (hideTimer.current) clearTimeout(hideTimer.current);
      hideTimer.current = setTimeout(() => setPhase("idle"), 4000);
    }
    return () => { if (hideTimer.current) clearTimeout(hideTimer.current); };
  }, [phase]);

  useEffect(() => {
    if (!openPopup) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (settingsBtnRef.current?.contains(target)) return;
      if (document.getElementById("art-settings-popup")?.contains(target)) return;
      if (toolbarRef.current && !toolbarRef.current.contains(target))
        setOpenPopup(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [openPopup]);

  useEffect(() => {
    if (!openPanel) {
      setArtPanelAnchor(null);
      return;
    }
    if (toolbarRef.current) {
      const rect = toolbarRef.current.getBoundingClientRect();
      setArtPanelAnchor({
        left: rect.left,
        bottom: window.innerHeight - rect.top,
        width: Math.max(artW, 360),
        height: Math.min(480, rect.top - 74),
      });
    }
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const insideToolbar = toolbarRef.current?.contains(target);
      const insidePopup = document.getElementById("art-panel-popup")?.contains(target);
      if (!insideToolbar && !insidePopup) setOpenPanel(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [openPanel, artW]);

  useEffect(() => {
    getArtModelOptions().then(setArtOptions).catch(() => {}).finally(() => setToolbarLoading(false));
  }, []);

  // Close popups/panels when other overlays open
  useEffect(() => {
    const handler = () => {
      if (emittingRef.current) return;
      setOpenPopup(null);
      setOpenPanel(null);
    };
    window.addEventListener("art-overlay-opened", handler);
    window.addEventListener("chat-picker-opened", handler);
    return () => {
      window.removeEventListener("art-overlay-opened", handler);
      window.removeEventListener("chat-picker-opened", handler);
    };
  }, []);

  const reloadActiveLoras = useCallback(async () => {
    try {
      const { listLoras } = await import("../../api/client");
      const data = await listLoras();
      setActiveLoras((data.loras ?? []).filter((l) => l.enabled).map((l) => ({ id: l.id, name: l.name })));
    } catch {}
  }, []);

  const reloadActiveEmbeddings = useCallback(async () => {
    try {
      const { listEmbeddings } = await import("../../api/client");
      const data = await listEmbeddings();
      setActiveEmbeddings((data.embeddings ?? []).filter((e) => e.enabled).map((e) => ({ id: e.id, name: e.name })));
    } catch {}
  }, []);

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

  const persist = (updates: Record<string, string>) =>
    savePromptData({ ...loadPromptData(), ...updates });

  const persistGen = (updates: Record<string, unknown>) =>
    updateSingleton("GeneratorSettings", updates).catch(() => {});

  const handleVersion = (v: string) => {
    setVersion(v); setModelPath(""); setScheduler("");
    try { localStorage.setItem("airunner_art_version", v); } catch {}
    updateSingleton("GeneratorSettings", { version: v, custom_path: "", scheduler: "" }).catch(() => {});
    window.dispatchEvent(new CustomEvent("art-version-changed", { detail: v }));
  };

  const handleModel = (m: string) => {
    setModelPath(m);
    try { localStorage.setItem("airunner_art_model", m); } catch {}
    updateSingleton("GeneratorSettings", { custom_path: m }).catch(() => {});
    window.dispatchEvent(new CustomEvent("art-model-changed", { detail: m }));
  };

  const handleScheduler = (s: string) => {
    setScheduler(s);
    try { localStorage.setItem("airunner_art_scheduler", s); } catch {}
    updateSingleton("GeneratorSettings", { scheduler: s }).catch(() => {});
  };

  const handleSeedChange = useCallback((v: number) => {
    setSeed(v); setSeedRandomized(false);
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
      setSeedRandomized(true); setSeed(s);
      try { localStorage.setItem("airunner_seed", String(-1)); } catch {}
      updateSingleton("GeneratorSettings", { seed: -1 }).catch(() => {});
    }
  }, [seed, seedRandomized]);

  const onGenerate = useCallback(async () => {
    if (!prompt.trim()) return;
    setPhase("loading");
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
          genWidth, genHeight,
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setPhase(msg === "Cancelled" ? "cancelled" : "failed");
    }
  }, [prompt, negativePrompt, genWidth, genHeight, canvasCtx, artGenerate]);

  const onCancel = useCallback(() => artCancel(), [artCancel]);

  const handleClearPrompts = () => {
    setPrompt(""); setNegativePrompt(""); setSecondaryPrompt(""); setSecondaryNegativePrompt("");
    persist({ prompt: "", negative_prompt: "", secondary_prompt: "", secondary_negative_prompt: "" });
  };

  const handleSavePrompt = async () => {
    if (!prompt.trim()) return;
    setSaving(true);
    try {
      await createSavedPrompt({ prompt, secondary_prompt: secondaryPrompt, negative_prompt: negativePrompt, secondary_negative_prompt: secondaryNegativePrompt });
    } catch {} finally { setSaving(false); }
  };

  const handleLoadPrompt = (p: SavedPrompt) => {
    setPrompt(p.prompt); setNegativePrompt(p.negative_prompt);
    setSecondaryPrompt(p.secondary_prompt); setSecondaryNegativePrompt(p.secondary_negative_prompt);
    persist({ prompt: p.prompt, negative_prompt: p.negative_prompt, secondary_prompt: p.secondary_prompt, secondary_negative_prompt: p.secondary_negative_prompt });
  };

  const collapseToStorage = (val: boolean) => {
    setCollapsed(val);
    try { localStorage.setItem(LS_COLLAPSED, String(val)); } catch {}
  };

  const togglePopup = (popup: NonNullable<ArtPopup>) => {
    setOpenPanel(null);
    setOpenPopup((prev) => {
      const next = prev === popup ? null : popup;
      if (next === "settings") {
        emittingRef.current = true;
        window.dispatchEvent(new Event("art-overlay-opened"));
        emittingRef.current = false;
        if (settingsBtnRef.current) {
          const r = settingsBtnRef.current.getBoundingClientRect();
          setSettingsAnchor({ left: r.left, bottom: window.innerHeight - r.top + 4 });
        }
      }
      return next;
    });
  };

  const togglePanel = (panel: NonNullable<ArtPanel>) => {
    setOpenPopup(null);
    setOpenPanel((prev) => {
      const next = prev === panel ? null : panel;
      if (next) {
        emittingRef.current = true;
        window.dispatchEvent(new Event("art-overlay-opened"));
        emittingRef.current = false;
      }
      return next;
    });
  };

  if (collapsed) {
    return (
      <div style={{
        width: 32, flexShrink: 0, display: "flex", flexDirection: "column",
        alignItems: "center", background: "var(--theme-panel-bg)",
        borderRight: "1px solid var(--separator-color)", padding: "4px 0", gap: 2, overflow: "hidden",
      }}>
        <button style={railBtnStyle} title="Expand art panel" onClick={() => collapseToStorage(false)}>
          <LucideIcon name="chevron-right" size={14} />
        </button>
        <div style={{ width: "60%", height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />
        <button style={railBtnStyle} title="Prompt" onClick={() => collapseToStorage(false)}>
          <LucideIcon name="message-square-heart" size={14} />
        </button>
      </div>
    );
  }

  return (
    <Fragment>
      <div style={{ width: artW, flexShrink: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Collapse header */}
        <div style={{
          display: "flex", alignItems: "center", flexShrink: 0,
          borderBottom: "1px solid var(--theme-border)", padding: "2px 4px",
        }}>
          <button
            type="button" onClick={() => collapseToStorage(true)} title="Collapse art panel"
            style={{ ...railBtnStyle, width: 24, height: 24, color: "var(--theme-text-secondary)", flexShrink: 0 }}
          >
            <LucideIcon name="chevron-left" size={13} />
          </button>
          <span style={{ fontSize: 10, fontWeight: 700, color: "var(--theme-text-secondary)", letterSpacing: "0.06em", paddingLeft: 4 }}>
            ART PROMPT
          </span>
        </div>

        {/* Main area */}
        <div className="d-flex flex-column flex-grow-1 overflow-hidden">
          {/* Prompt container — no margin, no border-radius */}
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            border: "none",
            borderRadius: 0,
            background: "var(--theme-input-bg)",
            overflow: "hidden",
            minHeight: 0,
          }}>
            <PromptTextareas
              prompt={prompt}
              secondaryPrompt={secondaryPrompt}
              negativePrompt={negativePrompt}
              secondaryNegativePrompt={secondaryNegativePrompt}
              isMultiPrompt={isMultiPrompt}
              generating={generating}
              onPromptChange={(v) => { setPrompt(v); persist({ prompt: v }); }}
              onSecondaryPromptChange={(v) => { setSecondaryPrompt(v); persist({ secondary_prompt: v }); }}
              onNegativePromptChange={(v) => { setNegativePrompt(v); persist({ negative_prompt: v }); }}
              onSecondaryNegativePromptChange={(v) => { setSecondaryNegativePrompt(v); persist({ secondary_negative_prompt: v }); }}
            />

            {/* Settings row */}
            <div style={{
              display: "flex", alignItems: "center", gap: 4,
              padding: "2px 6px",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              flexShrink: 0,
            }}>
              <div ref={settingsBtnRef}>
                <ToolbarIconBtn
                  title="Generation settings"
                  onClick={() => togglePopup("settings")}
                  active={openPopup === "settings"}
                >
                  <LucideIcon name="settings-2" size={14} />
                </ToolbarIconBtn>
              </div>
              {openPopup === "settings" && settingsAnchor && createPortal(
                <div id="art-settings-popup" style={{
                  position: "fixed",
                  left: settingsAnchor.left,
                  bottom: settingsAnchor.bottom,
                  background: "var(--theme-panel-bg)",
                  border: "1px solid rgba(255,255,255,0.14)",
                  borderRadius: 6,
                  zIndex: 1300,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                  maxHeight: 400,
                  overflowY: "auto",
                  minWidth: 260,
                }}>
                  <SettingsPopup
                    steps={steps}
                    cfgScale={cfgScale}
                    nSamples={nSamples}
                    imagesPerBatch={imagesPerBatch}
                    onStepsChange={(v) => { setSteps(v); saveToStorage("steps", v); persistGen({ steps: v }); }}
                    onCfgScaleChange={(v) => { setCfgScale(v); saveToStorage("cfg_scale", v); persistGen({ cfg_scale: v }); }}
                    onNSamplesChange={(v) => { setNSamples(v); saveToStorage("n_samples", v); persistGen({ n_samples: v }); }}
                    onImagesPerBatchChange={(v) => { setImagesPerBatch(v); saveToStorage("images_per_batch", v); persistGen({ images_per_batch: v }); }}
                  />
                </div>,
                document.body
              )}

              <span style={{ flex: 1 }} />

              <ToolbarIconBtn
                title={`LoRA${activeLoras.length > 0 ? ` (${activeLoras.length})` : ""}`}
                onClick={() => togglePanel("lora")}
                active={openPanel === "lora"}
                badge={activeLoras.length > 0 ? activeLoras.length : undefined}
              >
                <LucideIcon name="puzzle" size={14} />
              </ToolbarIconBtn>
              <ToolbarIconBtn
                title={`Embeddings${activeEmbeddings.length > 0 ? ` (${activeEmbeddings.length})` : ""}`}
                onClick={() => togglePanel("embeddings")}
                active={openPanel === "embeddings"}
                badge={activeEmbeddings.length > 0 ? activeEmbeddings.length : undefined}
              >
                <LucideIcon name="scan-text" size={14} />
              </ToolbarIconBtn>
            </div>

            <ModelRows
              version={version}
              modelPath={modelPath}
              scheduler={scheduler}
              schedulerOptions={availableSchedulers}
              loading={toolbarLoading}
              artOptions={artOptions}
              onVersionChange={handleVersion}
              onModelChange={handleModel}
              onSchedulerChange={handleScheduler}
            />

            {/* Seed/size row + submit row share a ref for outside-click and panel anchor */}
            <div ref={toolbarRef} style={{ flexShrink: 0, display: "flex", flexDirection: "column" }}>
              <PromptToolbar
                seed={seed}
                seedRandomized={seedRandomized}
                genWidth={genWidth}
                genHeight={genHeight}
                onSeedChange={handleSeedChange}
                onToggleRandom={handleToggleRandom}
                onWidthChange={(v) => { setGenWidth(v); saveToStorage("gen_width", v); persistGen({ width: v }); }}
                onHeightChange={(v) => { setGenHeight(v); saveToStorage("gen_height", v); persistGen({ height: v }); }}
              />
              <PromptControls
                generating={generating}
                progress={progress}
                phase={phase}
                hasPrompt={!!prompt.trim()}
                saving={saving}
                onClear={handleClearPrompts}
                onSave={handleSavePrompt}
                onToggleSavedPrompts={() => togglePanel("savedPrompts")}
                onGenerate={onGenerate}
                onCancel={onCancel}
              />
            </div>
          </div>
        </div>

      </div>
      <div
        className="resize-handle"
        onMouseDown={(e) => {
          e.preventDefault();
          artDragState = { startX: e.clientX, startW: artW, setW: setArtW };
          document.body.style.cursor = "col-resize";
          document.body.style.userSelect = "none";
        }}
      />

      {openPanel && artPanelAnchor && (
        <div
          id="art-panel-popup"
          style={{
            position: "fixed",
            left: artPanelAnchor.left,
            bottom: artPanelAnchor.bottom,
            width: artPanelAnchor.width,
            height: artPanelAnchor.height,
            zIndex: 1300,
            background: "var(--theme-panel-bg)",
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 0,
            boxShadow: "4px -4px 24px rgba(0,0,0,0.7)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {openPanel === "lora" && <LoraPanel />}
          {openPanel === "embeddings" && <EmbeddingsPanel />}
          {openPanel === "savedPrompts" && (
            <SavedPromptsPanel
              onLoad={handleLoadPrompt}
              onClose={() => setOpenPanel(null)}
            />
          )}
        </div>
      )}
    </Fragment>
  );
}
