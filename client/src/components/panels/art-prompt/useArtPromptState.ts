import { useState, useEffect, useCallback, useRef } from "react";
import { updateSingleton, getArtModelOptions } from "../../../api/client";
import type { ArtOptionsResponse } from "../../../api/client";
import { createSavedPrompt } from "../../../api/art";
import type { SavedPrompt } from "../../../api/art";
import { loadFromStorage } from "../art-model/ArtModelStorage";
import { loadPromptData, savePromptData } from "./ArtPromptStorage";
import { useCanvasContext } from "../../../features/canvas/CanvasContext";
import {
  renderVisibleComposite,
  cropToRect,
  renderInpaintMask,
  renderInpaintAlphaMask,
  compositeInpaintResult,
} from "../../../features/canvas/compositeCanvas";

/** Decode a data-URL into an HTMLImageElement (null on error). */
function loadDataUrlImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const el = new window.Image();
    el.onload = () => resolve(el);
    el.onerror = () => resolve(null);
    el.src = src;
  });
}
import { useArtWebSocket } from "../../../features/art/useArtWebSocket";
import type { ArtPopup, ArtPanel } from "./ArtShared";

export const ART_PANEL_DEFAULT = 300;
export const ART_PANEL_MIN = 220;
export const ART_PANEL_MAX = 520;
export const LS_ART_W = "airunner_art_panel_w";
export const LS_COLLAPSED = "canvas_art_panel_collapsed";

type Phase = "idle" | "loading" | "completed" | "cancelled" | "failed";

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
const verModelKey = (v: string) => `airunner_art_model_${v}`;
const verSchedulerKey = (v: string) => `airunner_art_scheduler_${v}`;

/** Variant versions whose LoRA/embedding files are stored under the base version's directory. */
const VARIANT_BASE: Record<string, string> = {
  "SDXL Lightning": "SDXL 1.0",
  "SDXL Hyper": "SDXL 1.0",
};

/** Resolve the directory name used for LoRA/embedding path filtering for a version. */
function baseDirForVersion(v: string): string {
  return VARIANT_BASE[v] || v;
}

export function useArtPromptState(opts?: {
  /** Effective generation type when driven externally (e.g. CanvasPanel). */
  generationType?: "txt2img" | "img2img" | "inpaint";
}) {
  const initial = loadPromptData();

  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(LS_COLLAPSED) === "true"; } catch { return false; }
  });
  const [artW, setArtW] = useState(() => loadNum(LS_ART_W, ART_PANEL_DEFAULT));
  useEffect(() => { saveNum(LS_ART_W, artW); }, [artW]);

  const [generationType, setGenerationType] = useState<"txt2img" | "img2img" | "inpaint">(
    () => {
      try { return (localStorage.getItem("airunner_gen_type") as "txt2img" | "img2img" | "inpaint") || "txt2img"; }
      catch { return "txt2img"; }
    }
  );

  const [prompt, setPrompt] = useState(initial.prompt);
  const [negativePrompt, setNegativePrompt] = useState(initial.negative_prompt);
  const [secondaryPrompt, setSecondaryPrompt] = useState(initial.secondary_prompt);
  const [secondaryNegativePrompt, setSecondaryNegativePrompt] = useState(initial.secondary_negative_prompt);

  const [activeLoras, setActiveLoras] = useState<{ id: number; name: string }[]>([]);
  const [activeEmbeddings, setActiveEmbeddings] = useState<{ id: number; name: string }[]>([]);

  const [artOptions, setArtOptions] = useState<ArtOptionsResponse | null>(null);
  const [version, setVersion] = useState(() => ls("airunner_art_version"));
  const [modelPath, setModelPath] = useState(() => {
    const v = ls("airunner_art_version");
    if (v) {
      const saved = ls(verModelKey(v));
      if (saved) return saved;
    }
    return ls("airunner_art_model");
  });
  const [scheduler, setScheduler] = useState(() => {
    const v = ls("airunner_art_version");
    if (v) {
      const saved = ls(verSchedulerKey(v));
      if (saved) return saved;
    }
    return ls("airunner_art_scheduler");
  });
  const [toolbarLoading, setToolbarLoading] = useState(true);

  const [saving, setSaving] = useState(false);

  const [openPopup, setOpenPopup] = useState<ArtPopup>(null);
  const [openPanel, setOpenPanel] = useState<ArtPanel>(null);
  const [artPanelAnchor, setArtPanelAnchor] = useState<{ left: number; bottom: number; width: number; height: number } | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<HTMLDivElement>(null);
  const settingsBtnRef = useRef<HTMLDivElement>(null);
  const promptBtnRef = useRef<HTMLDivElement>(null);
  const [settingsAnchor, setSettingsAnchor] = useState<{ left: number; bottom: number } | null>(null);
  const [promptSettingsAnchor, setPromptSettingsAnchor] = useState<{ left: number; bottom: number } | null>(null);
  const emittingRef = useRef(false);

  const availableSchedulers = (artOptions?.versions?.find((v) => v.name === version)?.schedulers) ?? [];

  const [genWidth, setGenWidth] = useState(() => loadFromStorage("gen_width", 512));
  const [genHeight, setGenHeight] = useState(() => loadFromStorage("gen_height", 512));
  const [nSamples, setNSamples] = useState(() => loadFromStorage("n_samples", 1));
  const [imagesPerBatch, setImagesPerBatch] = useState(() => loadFromStorage("images_per_batch", 1));
  const [steps, setSteps] = useState(() => loadFromStorage("steps", 20));
  const [cfgScale, setCfgScale] = useState(() => loadFromStorage("cfg_scale", 7.5));

  // img2img denoise strength / inpaint mask feather, both 0–1.
  const [strength, setStrengthState] = useState(() => loadNum("airunner_img2img_strength", 0.75));
  const [feather, setFeatherState] = useState(() => loadNum("airunner_inpaint_feather", 0));
  const setStrength = useCallback((v: number) => {
    setStrengthState(v);
    saveNum("airunner_img2img_strength", v);
  }, []);
  const setFeather = useCallback((v: number) => {
    setFeatherState(v);
    saveNum("airunner_inpaint_feather", v);
  }, []);

  const [seed, setSeed] = useState(() => {
    try {
      const v = Number(localStorage.getItem("airunner_seed") || "0");
      if (v === -1) {
        // Random mode was on before reload — restore the saved seed
        // rather than generating a fresh random number.
        const saved = localStorage.getItem("airunner_seed_saved");
        if (saved !== null) {
          const n = Number(saved);
          if (!isNaN(n)) return n;
        }
        // No saved seed available (e.g. first load after update) —
        // default to 0 instead of returning the -1 sentinel.
        return 0;
      }
      return v;
    } catch { return 0; }
  });
  const [seedRandomized, setSeedRandomized] = useState(() => {
    try { return Number(localStorage.getItem("airunner_seed") || "0") === -1; }
    catch { return false; }
  });

  const [phase, setPhase] = useState<Phase>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  let canvasCtx: ReturnType<typeof useCanvasContext> | null = null;
  try { canvasCtx = useCanvasContext(); } catch {}

  // ── Effective generation size ───────────────────────────────────────────
  // For img2img / inpaint the active generation area *is* the generation size:
  // its width/height drive the request and the size controls edit it (clamped
  // to the canvas). txt2img keeps its own genWidth/genHeight.
  const effGenType = opts?.generationType ?? generationType;
  const isAreaMode =
    (effGenType === "img2img" || effGenType === "inpaint") && !!canvasCtx;
  const area = canvasCtx?.activeGridArea ?? null;
  const effGenWidth = isAreaMode && area ? area.width : genWidth;
  const effGenHeight = isAreaMode && area ? area.height : genHeight;

  const setEffGenWidth = useCallback((w: number) => {
    if (isAreaMode && canvasCtx && area) {
      const cw = canvasCtx.documentWidth;
      const ch = canvasCtx.documentHeight;
      const nw = Math.min(Math.max(8, w), cw);
      const nx = Math.min(area.x, Math.max(0, cw - nw));
      canvasCtx.setActiveGridArea({ ...area, x: nx, width: nw, height: Math.min(area.height, ch) });
    } else {
      setGenWidth(w);
    }
  }, [isAreaMode, canvasCtx, area]);

  const setEffGenHeight = useCallback((h: number) => {
    if (isAreaMode && canvasCtx && area) {
      const cw = canvasCtx.documentWidth;
      const ch = canvasCtx.documentHeight;
      const nh = Math.min(Math.max(8, h), ch);
      const ny = Math.min(area.y, Math.max(0, ch - nh));
      canvasCtx.setActiveGridArea({ ...area, y: ny, height: nh, width: Math.min(area.width, cw) });
    } else {
      setGenHeight(h);
    }
  }, [isAreaMode, canvasCtx, area]);

  // Seed the generation area from the chosen size (clamped + centered) when
  // switching *into* area mode mid-session, so it lines up with the last
  // txt2img size. Initialised to the first-render value so a reload that starts
  // in img2img/inpaint keeps the persisted area instead of recentering it.
  const prevAreaMode = useRef(isAreaMode);
  useEffect(() => {
    if (isAreaMode && canvasCtx && !prevAreaMode.current) {
      const cw = canvasCtx.documentWidth;
      const ch = canvasCtx.documentHeight;
      const w = Math.min(genWidth, cw);
      const h = Math.min(genHeight, ch);
      canvasCtx.setActiveGridArea({
        width: w,
        height: h,
        x: Math.round((cw - w) / 2),
        y: Math.round((ch - h) / 2),
      });
    }
    prevAreaMode.current = isAreaMode;
    // genWidth/genHeight intentionally excluded: only re-seed on mode entry.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAreaMode, canvasCtx]);

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
      hideTimer.current = setTimeout(() => {
        setPhase("idle");
        setErrorMessage(null);
      }, 4000);
    }
    return () => { if (hideTimer.current) clearTimeout(hideTimer.current); };
  }, [phase]);

  useEffect(() => {
    if (!openPopup) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (settingsBtnRef.current?.contains(target)) return;
      if (promptBtnRef.current?.contains(target)) return;
      if (document.getElementById("art-settings-popup")?.contains(target)) return;
      if (document.getElementById("art-prompt-settings-popup")?.contains(target)) return;
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
    const anchorRef = controlsRef.current ?? toolbarRef.current;
    if (anchorRef) {
      const rect = anchorRef.getBoundingClientRect();
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
      const { listLoras } = await import("../../../api/client");
      const data = await listLoras();
      setActiveLoras((data.loras ?? []).filter((l) => l.enabled).map((l) => ({ id: l.id, name: l.name })));
    } catch {}
  }, []);

  const reloadActiveEmbeddings = useCallback(async () => {
    try {
      const { listEmbeddings } = await import("../../../api/client");
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

  const handleVersion = async (v: string) => {
    // 1. Save current version's enabled LoRA/embedding IDs, then disable them
    if (version && version !== v) {
      try {
        localStorage.setItem(
          `airunner_enabled_loras_${version}`,
          JSON.stringify(activeLoras.map((l) => l.id)),
        );
        localStorage.setItem(
          `airunner_enabled_embeddings_${version}`,
          JSON.stringify(activeEmbeddings.map((e) => e.id)),
        );
      } catch {}

      // Disable all currently enabled LoRAs and embeddings
      const disablePromises: Promise<unknown>[] = [];
      for (const lora of activeLoras) {
        disablePromises.push(
          (async () => {
            try {
              const { updateLora } = await import("../../../api/client");
              await updateLora(lora.id, { enabled: false });
            } catch { /* item may have been deleted */ }
          })(),
        );
      }
      for (const emb of activeEmbeddings) {
        disablePromises.push(
          (async () => {
            try {
              const { updateEmbedding } = await import("../../../api/client");
              await updateEmbedding(emb.id, { enabled: false });
            } catch { /* item may have been deleted */ }
          })(),
        );
      }
      await Promise.all(disablePromises);
    }

    // 2. Save current model/scheduler under the old version before switching
    if (version) {
      try { localStorage.setItem(verModelKey(version), modelPath); } catch {}
      try { localStorage.setItem(verSchedulerKey(version), scheduler); } catch {}
    }

    // 3. Load saved settings for the new version (if any)
    const savedModel = (() => {
      const m = ls(verModelKey(v));
      if (m) return m;
      return "";
    })();
    const savedScheduler = (() => {
      const s = ls(verSchedulerKey(v));
      if (s) return s;
      return "";
    })();

    // 4. Switch version immediately
    setVersion(v);
    setModelPath(savedModel);
    setScheduler(savedScheduler);

    try { localStorage.setItem("airunner_art_version", v); } catch {}
    try { localStorage.setItem("airunner_art_model", savedModel); } catch {}
    try { localStorage.setItem("airunner_art_scheduler", savedScheduler); } catch {}

    updateSingleton("GeneratorSettings", {
      version: v,
      custom_path: savedModel,
      scheduler: savedScheduler,
    }).catch(() => {});
    window.dispatchEvent(new CustomEvent("art-version-changed", { detail: v }));

    // 5. Restore the new version's previously-enabled LoRAs/embeddings
    const prevLoraIds: number[] = (() => {
      try {
        const raw = localStorage.getItem(`airunner_enabled_loras_${v}`);
        return raw ? (JSON.parse(raw) as number[]) : [];
      } catch { return []; }
    })();
    const prevEmbIds: number[] = (() => {
      try {
        const raw = localStorage.getItem(`airunner_enabled_embeddings_${v}`);
        return raw ? (JSON.parse(raw) as number[]) : [];
      } catch { return []; }
    })();

    if (prevLoraIds.length > 0 || prevEmbIds.length > 0) {
      try {
        const { listLoras, listEmbeddings } = await import("../../../api/client");
        const [loraData, embData] = await Promise.all([
          listLoras(),
          listEmbeddings(),
        ]);

        const baseDir = baseDirForVersion(v);

        const lorasToRestore = (loraData.loras ?? [])
          .filter(
            (l) =>
              prevLoraIds.includes(l.id) &&
              (l.path || "").includes(`/${baseDir}/`),
          );
        const embsToRestore = (embData.embeddings ?? [])
          .filter(
            (e) =>
              prevEmbIds.includes(e.id) &&
              (e.path || "").includes(`/${baseDir}/`),
          );

        const restorePromises: Promise<unknown>[] = [
          ...lorasToRestore.map((l) =>
            (async () => {
              try {
                const { updateLora } = await import("../../../api/client");
                await updateLora(l.id, { enabled: true });
              } catch { /* */ }
            })(),
          ),
          ...embsToRestore.map((e) =>
            (async () => {
              try {
                const { updateEmbedding } = await import("../../../api/client");
                await updateEmbedding(e.id, { enabled: true });
              } catch { /* */ }
            })(),
          ),
        ];

        await Promise.all(restorePromises);
      } catch { /* */ }
    }

    // Always refresh badge state after version switch, regardless of
    // whether there were previous items to restore.
    window.dispatchEvent(new CustomEvent("lora-changed"));
    window.dispatchEvent(new CustomEvent("embedding-changed"));
  };

  const handleModel = (m: string) => {
    setModelPath(m);
    try { localStorage.setItem("airunner_art_model", m); } catch {}
    if (version) {
      try { localStorage.setItem(verModelKey(version), m); } catch {}
    }
    updateSingleton("GeneratorSettings", { custom_path: m }).catch(() => {});
    window.dispatchEvent(new CustomEvent("art-model-changed", { detail: m }));
  };

  const handleScheduler = (s: string) => {
    setScheduler(s);
    try { localStorage.setItem("airunner_art_scheduler", s); } catch {}
    if (version) {
      try { localStorage.setItem(verSchedulerKey(version), s); } catch {}
    }
    updateSingleton("GeneratorSettings", { scheduler: s }).catch(() => {});
  };

  const handleSeedChange = useCallback((v: number) => {
    setSeed(v); setSeedRandomized(false);
    try { localStorage.setItem("airunner_seed", String(v)); } catch {}
    updateSingleton("GeneratorSettings", { seed: v }).catch(() => {});
  }, []);

  const handleToggleRandom = useCallback(() => {
    if (seedRandomized) {
      // Turning OFF random: persist the current seed so it's reused
      setSeedRandomized(false);
      try { localStorage.setItem("airunner_seed", String(seed)); } catch {}
      updateSingleton("GeneratorSettings", { seed }).catch(() => {});
    } else {
      // Turning ON random: persist the current seed so it survives
      // page reload, then mark as randomized. The actual randomization
      // happens at submit time.
      try { localStorage.setItem("airunner_seed_saved", String(seed)); } catch {}
      setSeedRandomized(true);
      try { localStorage.setItem("airunner_seed", String(-1)); } catch {}
      updateSingleton("GeneratorSettings", { seed: -1 }).catch(() => {});
    }
  }, [seed, seedRandomized]);

  const onGenerate = useCallback(async () => {
    if (!prompt.trim()) return;
    const genType = effGenType;
    setPhase("loading");
    setErrorMessage(null);
    // If random seed is enabled, generate a fresh seed right before
    // the request so each submission gets a new random value.
    // Update state + localStorage so the UI reflects the used seed.
    const effectiveSeed: number | undefined = seedRandomized
      ? Math.floor(Math.random() * 2147483647) + 1
      : seed;
    if (seedRandomized && effectiveSeed !== undefined) {
      setSeed(effectiveSeed);
      // Keep the -1 sentinel in "airunner_seed" so the randomized toggle
      // is restored as ON after a reload. Persist the actual value used in
      // "airunner_seed_saved" only (used to display/reuse the seed).
      try { localStorage.setItem("airunner_seed_saved", String(effectiveSeed)); } catch {}
    }

    // For img2img / inpaint, the active generation area is both the output size
    // and the capture/placement region. Composite the visible layers, crop to
    // the area, and (for inpaint) build a white-on-black mask from the magenta
    // strokes. The daemon decodes raw base64, so the data: prefix is stripped.
    const isImageMode =
      (genType === "img2img" || genType === "inpaint") && !!canvasCtx && !!area;
    let outWidth = effGenWidth;
    let outHeight = effGenHeight;
    let imageB64: string | undefined;
    let maskB64: string | undefined;
    // Kept for inpaint result compositing.
    let originalCrop: HTMLCanvasElement | undefined;
    if (isImageMode && canvasCtx && area) {
      outWidth = area.width;
      outHeight = area.height;
      const composite = await renderVisibleComposite({
        layers: canvasCtx.layers,
        layerGroups: canvasCtx.layerGroups,
        displayOrder: canvasCtx.displayOrder,
        documentWidth: canvasCtx.documentWidth,
        documentHeight: canvasCtx.documentHeight,
      });
      if (composite) {
        originalCrop = cropToRect(composite, area);
        imageB64 = originalCrop.toDataURL("image/png").split(",")[1];
      }
      if (genType === "inpaint") {
        const mask = renderInpaintMask(canvasCtx.inpaintMaskStrokes, area, feather);
        maskB64 = mask.toDataURL("image/png").split(",")[1];
      }
    }

    try {
      const imageBase64 = await artGenerate({
        prompt: prompt.trim(),
        negativePrompt: negativePrompt?.trim() || undefined,
        seed: effectiveSeed,
        artModel: ls("airunner_art_model") || undefined,
        artVersion: ls("airunner_art_version") || undefined,
        scheduler: ls("airunner_art_scheduler") || undefined,
        width: outWidth,
        height: outHeight,
        ...(imageB64
          ? { pipeline: genType, imageB64, strength }
          : {}),
        ...(maskB64 ? { maskB64 } : {}),
      });
      setPhase("completed");
      if (imageBase64 && canvasCtx) {
        if (isImageMode && area) {
          // For inpaint, composite the result so only the masked region
          // replaces the original — unmasked pixels are preserved exactly,
          // regardless of how the backend pipeline behaved.
          let placed = `data:image/png;base64,${imageBase64}`;
          if (genType === "inpaint" && originalCrop) {
            const gen = await loadDataUrlImage(placed);
            if (gen) {
              const alpha = renderInpaintAlphaMask(
                canvasCtx.inpaintMaskStrokes, area, feather,
              );
              placed = compositeInpaintResult(originalCrop, gen, alpha)
                .toDataURL("image/png");
            }
          }
          canvasCtx.placeImageOnNewLayer(
            placed, area.x, area.y, area.width, area.height,
          );
        } else {
          const docW = canvasCtx.documentWidth ?? outWidth;
          const docH = canvasCtx.documentHeight ?? outHeight;
          canvasCtx.placeImageOnNewLayer(
            imageBase64,
            Math.round((docW - outWidth) / 2),
            Math.round((docH - outHeight) / 2),
            outWidth, outHeight,
          );
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setPhase(msg === "Cancelled" ? "cancelled" : "failed");
      if (msg !== "Cancelled") {
        setErrorMessage(msg);
      }
    }
  }, [prompt, negativePrompt, effGenWidth, effGenHeight, canvasCtx, area, artGenerate, seed, seedRandomized, effGenType, strength, feather]);

  const onCancel = useCallback(() => artCancel(), [artCancel]);

  const handleClearPrompts = () => {
    setPrompt(""); setNegativePrompt(""); setSecondaryPrompt(""); setSecondaryNegativePrompt("");
    persist({ prompt: "", negative_prompt: "", secondary_prompt: "", secondary_negative_prompt: "" });
  };

  const handleSavePrompt = async () => {
    if (!prompt.trim()) return;
    setSaving(true);
    try {
      await createSavedPrompt({
        version: version || undefined,
        prompt,
        secondary_prompt: secondaryPrompt,
        negative_prompt: negativePrompt,
        secondary_negative_prompt: secondaryNegativePrompt,
      });
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
      } else if (next === "promptSettings") {
        emittingRef.current = true;
        window.dispatchEvent(new Event("art-overlay-opened"));
        emittingRef.current = false;
        if (promptBtnRef.current) {
          const r = promptBtnRef.current.getBoundingClientRect();
          setPromptSettingsAnchor({ left: r.left, bottom: window.innerHeight - r.top + 4 });
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

  return {
    collapsed, collapseToStorage,
    artW, setArtW,
    prompt, setPrompt,
    negativePrompt, setNegativePrompt,
    secondaryPrompt, setSecondaryPrompt,
    secondaryNegativePrompt, setSecondaryNegativePrompt,
    activeLoras, activeEmbeddings,
    artOptions, version, modelPath, scheduler, toolbarLoading,
    saving,
    openPopup, openPanel, artPanelAnchor,
    toolbarRef, controlsRef, settingsBtnRef, promptBtnRef,
    settingsAnchor, promptSettingsAnchor,
    availableSchedulers,
    genWidth: effGenWidth, setGenWidth: setEffGenWidth,
    genHeight: effGenHeight, setGenHeight: setEffGenHeight,
    nSamples, setNSamples,
    imagesPerBatch, setImagesPerBatch,
    steps, setSteps,
    cfgScale, setCfgScale,
    strength, setStrength,
    feather, setFeather,
    seed, seedRandomized,
    phase,
    errorMessage,
    setErrorMessage,
    generating, progress,
    isMultiPrompt,
    persist, persistGen,
    handleVersion, handleModel, handleScheduler,
    handleSeedChange, handleToggleRandom,
    onGenerate, onCancel,
    generationType, setGenerationType,
    handleClearPrompts, handleSavePrompt, handleLoadPrompt,
    togglePopup, togglePanel,
  };
}
