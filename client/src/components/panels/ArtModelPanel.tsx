import { useState, useEffect } from "react";
import {
  getSingleton,
  updateSingleton,
  getArtModelOptions,
} from "../../api/client";
import type { ArtOptionsResponse } from "../../api/client";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_MODEL_STATUS } from "../../features/events/types";
import VersionSelector from "./art-model/VersionSelector";
import ModelSelector from "./art-model/ModelSelector";
import SchedulerSelector from "./art-model/SchedulerSelector";
import SeedControls from "./art-model/SeedControls";
import VRAMEstimate from "./art-model/VRAMEstimate";
import ArtModelSliders from "./art-model/ArtModelSliders";
import {
  saveToStorage,
  loadFromStorage,
} from "./art-model/ArtModelStorage";

export default function ArtModelPanel() {
  const [version, setVersion] = useState("");
  const [modelPath, setModelPath] = useState("");
  const [scheduler, setScheduler] = useState("");

  const [options, setOptions] = useState<ArtOptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const [nSamples, setNSamples] = useState(
    loadFromStorage("n_samples", 1),
  );
  const [imagesPerBatch, setImagesPerBatch] = useState(
    loadFromStorage("images_per_batch", 1),
  );
  const [steps, setSteps] = useState(loadFromStorage("steps", 20));
  const [cfgScale, setCfgScale] = useState(
    loadFromStorage("cfg_scale", 7.5),
  );
  const [seed, setSeed] = useState(0);
  const [seedRandomized, setSeedRandomized] = useState(false);
  const [vramEstimate, setVramEstimate] = useState<number | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      const v = (e as CustomEvent).detail as string;
      setVersion(v);
      setModelPath("");
      setScheduler("");
      try { localStorage.setItem("airunner_art_version", v); } catch {}
    };
    window.addEventListener("art-version-changed", handler);
    const modelHandler = (e: Event) => {
      const m = (e as CustomEvent).detail as string;
      setModelPath(m ?? "");
    };
    window.addEventListener("art-model-changed", modelHandler);
    return () => {
      window.removeEventListener("art-version-changed", handler);
      window.removeEventListener("art-model-changed", modelHandler);
    };
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const opts = await getArtModelOptions();
        setOptions(opts);
      } catch { /* */ }

      const _ls = (k: string) => {
        try { return localStorage.getItem(k) || ""; } catch { return ""; }
      };
      try {
        const r = await getSingleton("GeneratorSettings");
        const savedVersion = String(r.version ?? "");
        // DB column is custom_path (not model_path)
        const savedModelPath = String(r.custom_path ?? "");
        const savedScheduler = String(r.scheduler ?? "");

        // Server returned values — use them
        if (savedVersion) {
          setVersion(savedVersion);
          try { localStorage.setItem("airunner_art_version", savedVersion); } catch {}
        } else {
          // Server returned empty — try localStorage
          const fv = _ls("airunner_art_version");
          if (fv) setVersion(fv);
        }
        if (savedModelPath) {
          setModelPath(savedModelPath);
          try { localStorage.setItem("airunner_art_model", savedModelPath); } catch {}
        } else {
          const fm = _ls("airunner_art_model");
          if (fm) setModelPath(fm);
        }
        if (savedScheduler) {
          setScheduler(savedScheduler);
        } else {
          const fs = _ls("airunner_art_scheduler");
          if (fs) setScheduler(fs);
        }

      } catch {
        // Server unavailable — fall back to localStorage
        const fv = _ls("airunner_art_version");
        const fm = _ls("airunner_art_model");
        const fs = _ls("airunner_art_scheduler");
        if (fv) setVersion(fv);
        if (fm) setModelPath(fm);
        if (fs) setScheduler(fs);
      }
      // Seed is always restored from localStorage to survive server restarts.
      // -1 is the sentinel for "randomize each run" — generate a fresh number
      // so the field always shows a real seed value, never -1.
      try {
        const seedVal = Number(
          (() => { try { return localStorage.getItem("airunner_seed") || "0"; } catch { return "0"; } })(),
        );
        if (seedVal === -1) {
          const freshSeed = Math.floor(Math.random() * 2147483647) + 1;
          setSeed(freshSeed);
          setSeedRandomized(true);
        } else {
          setSeed(seedVal);
          setSeedRandomized(false);
        }
      } catch { /* */ }

      try {
        const r = await getSingleton("VRAMEstimate");
        const gb = Number(
          (r as Record<string, unknown>).file_size_gb ?? 0,
        );
        if (gb > 0) setVramEstimate(gb);
      } catch { /* */ }

      setLoading(false);
    })();
  }, []);

  useEventBus([EVENT_MODEL_STATUS], () => {
    (async () => {
      try {
        const opts = await getArtModelOptions();
        setOptions(opts);
      } catch { /* */ }
    })();
  }, []);

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("GeneratorSettings", updates).catch(() => {});
  };

  const versionInfo = options?.versions?.find((v) => v.name === version);
  const availableModels = versionInfo?.models ?? [];
  const availableSchedulers = versionInfo?.schedulers ?? [];

  const handleVersionChange = (v: string) => {
    setVersion(v);
    setModelPath("");
    setScheduler("");
    persist({ version: v, custom_path: "", scheduler: "" });
    try { localStorage.setItem("airunner_art_version", v); } catch {}
    window.dispatchEvent(
      new CustomEvent("art-version-changed", { detail: v }),
    );
  };

  const handleModelChange = (m: string) => {
    setModelPath(m);
    persist({ custom_path: m });
    try { localStorage.setItem("airunner_art_model", m); } catch {}
    window.dispatchEvent(
      new CustomEvent("art-model-changed", { detail: m }),
    );
  };

  const toggleSeedRandom = () => {
    if (seedRandomized) {
      setSeedRandomized(false);
      try { localStorage.setItem("airunner_seed", String(seed)); } catch {}
      persist({ seed });
    } else {
      const s = Math.floor(Math.random() * 2147483647) + 1;
      setSeedRandomized(true);
      setSeed(s);
      try { localStorage.setItem("airunner_seed", String(-1)); } catch {}
      persist({ seed: -1 });
    }
  };

  return (
    <div className="p-2">
      <div className="d-flex align-items-center gap-2 mb-2">
        <h6 style={{ color: "var(--theme-text-secondary)" }} className="mb-0">
          Art Model Settings
        </h6>
        {loading && (
          <div
            className="spinner-border spinner-border-sm"
            role="status"
            style={{
              color: "var(--theme-text-secondary)",
              width: 12,
              height: 12,
            }}
          />
        )}
      </div>

      {/* Version + Model (2-col), then Scheduler (full-width) */}
      <div className="row g-1 mb-1">
        <div className="col-6">
          <VersionSelector
            versions={options?.versions ?? []}
            value={version}
            loading={loading}
            onChange={handleVersionChange}
          />
        </div>
        <div className="col-6">
          <ModelSelector
            models={availableModels}
            value={modelPath}
            loading={loading}
            hasVersion={!!version}
            onChange={handleModelChange}
          />
        </div>
        <div className="col-12">
          <SchedulerSelector
            schedulers={availableSchedulers}
            value={scheduler}
            loading={loading}
            hasVersion={!!version}
            onChange={(v) => {
              setScheduler(v);
              persist({ scheduler: v });
            }}
          />
        </div>
      </div>

      <hr className="border-secondary" />

      {/* 2-column grid: sliders + seed + VRAM */}
      <div className="row g-1">
        <ArtModelSliders
          nSamples={nSamples}
          imagesPerBatch={imagesPerBatch}
          steps={steps}
          cfgScale={cfgScale}
          onNSamplesChange={(v) => {
            setNSamples(v);
            saveToStorage("n_samples", v);
            persist({ n_samples: v });
          }}
          onImagesPerBatchChange={(v) => {
            setImagesPerBatch(v);
            saveToStorage("images_per_batch", v);
            persist({ images_per_batch: v });
          }}
          onStepsChange={(v) => {
            setSteps(v);
            saveToStorage("steps", v);
            persist({ steps: v });
          }}
          onCfgScaleChange={(v) => {
            setCfgScale(v);
            saveToStorage("cfg_scale", v);
            persist({ cfg_scale: v });
          }}
        />
        <div className="col-12">
          <SeedControls
            seed={seed}
            seedRandomized={seedRandomized}
            loading={loading}
            onSeedChange={(v) => {
              setSeed(v);
              setSeedRandomized(false);
              try { localStorage.setItem("airunner_seed", String(v)); } catch {}
              persist({ seed: v });
            }}
            onToggleRandom={toggleSeedRandom}
          />
        </div>
        <div className="col-6">
          <VRAMEstimate vramGb={vramEstimate} />
        </div>
      </div>
    </div>
  );
}
