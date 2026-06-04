import { useState, useEffect } from "react";
import {
  getSingleton,
  updateSingleton,
} from "../../api/client";
import type { ArtOptionsResponse } from "../../api/client";
import { BASE_URL } from "../../types/api";
import VersionSelector from "./art-model/VersionSelector";
import ModelSelector from "./art-model/ModelSelector";
import SchedulerSelector from "./art-model/SchedulerSelector";
import PrecisionSelector from "./art-model/PrecisionSelector";
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
  const [precision, setPrecision] = useState("");

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
  const [width, setWidth] = useState(loadFromStorage("width", 1024));
  const [height, setHeight] = useState(
    loadFromStorage("height", 1024),
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
        const opts = await import("../../api/client").then(
          (m) => m.getArtModelOptions(),
        );
        setOptions(opts);
      } catch { /* */ }

      try {
        const r = await getSingleton("GeneratorSettings");
        const savedVersion = String(r.version ?? "");
        setVersion(savedVersion);
        setModelPath(String(r.model_path ?? ""));
        setScheduler(String(r.scheduler ?? ""));
        setPrecision(String(r.dtype ?? ""));
        try {
          localStorage.setItem("airunner_art_version", savedVersion);
        } catch {}
        if (r.model_path) {
          try {
            localStorage.setItem(
              "airunner_art_model",
              String(r.model_path),
            );
          } catch {}
        }
        const savedSeed = Number(r.seed ?? 0);
        setSeed(savedSeed);
        setSeedRandomized(savedSeed === -1);
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

  useEffect(() => {
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/art/models/watch`,
    );
    eventSource.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "reload") {
          (async () => {
            try {
              const opts = await import("../../api/client").then(
                (m) => m.getArtModelOptions(),
              );
              setOptions(opts);
            } catch { /* */ }
          })();
        }
      } catch { /* ignore malformed events */ }
    });
    eventSource.onerror = () => {
      // The browser will automatically reconnect EventSource on error
    };
    return () => {
      eventSource.close();
    };
  }, []);

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("GeneratorSettings", updates).catch(() => {});
  };

  const versionInfo = options?.versions?.find((v) => v.name === version);
  const availableModels = versionInfo?.models ?? [];
  const availableSchedulers = versionInfo?.schedulers ?? [];
  const precisions = options?.precisions ?? [];

  const handleVersionChange = (v: string) => {
    setVersion(v);
    setModelPath("");
    setScheduler("");
    persist({ version: v, model_path: "", scheduler: "" });
    try { localStorage.setItem("airunner_art_version", v); } catch {}
    window.dispatchEvent(
      new CustomEvent("art-version-changed", { detail: v }),
    );
  };

  const handleModelChange = (m: string) => {
    setModelPath(m);
    persist({ model_path: m });
    try { localStorage.setItem("airunner_art_model", m); } catch {}
    window.dispatchEvent(
      new CustomEvent("art-model-changed", { detail: m }),
    );
  };

  const toggleSeedRandom = () => {
    if (seedRandomized) {
      setSeedRandomized(false);
      persist({ seed });
    } else {
      const s = Math.floor(Math.random() * 2147483647) + 1;
      setSeedRandomized(true);
      setSeed(s);
      persist({ seed: -1 });
    }
  };

  return (
    <div className="p-2">
      <div className="d-flex align-items-center gap-2 mb-2">
        <h6 style={{ color: "var(--theme-text-secondary)" }} className="mb-0">
          Art Model
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

      <VersionSelector
        versions={options?.versions ?? []}
        value={version}
        loading={loading}
        onChange={handleVersionChange}
      />

      <ModelSelector
        models={availableModels}
        value={modelPath}
        loading={loading}
        hasVersion={!!version}
        onChange={handleModelChange}
      />

      <SchedulerSelector
        schedulers={availableSchedulers}
        value={scheduler}
        loading={loading}
        onChange={(v) => {
          setScheduler(v);
          persist({ scheduler: v });
        }}
      />

      <PrecisionSelector
        precisions={precisions}
        value={precision}
        loading={loading}
        onChange={(v) => {
          setPrecision(v);
          persist({ dtype: v });
        }}
      />

      <VRAMEstimate vramGb={vramEstimate} />

      <hr className="border-secondary" />

      <ArtModelSliders
        nSamples={nSamples}
        imagesPerBatch={imagesPerBatch}
        steps={steps}
        cfgScale={cfgScale}
        width={width}
        height={height}
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
        onWidthChange={(v) => {
          setWidth(v);
          saveToStorage("width", v);
          persist({ width: v });
        }}
        onHeightChange={(v) => {
          setHeight(v);
          saveToStorage("height", v);
          persist({ height: v });
        }}
      />

      <SeedControls
        seed={seed}
        seedRandomized={seedRandomized}
        loading={loading}
        onSeedChange={(v) => {
          setSeed(v);
          setSeedRandomized(false);
          persist({ seed: v });
        }}
        onToggleRandom={toggleSeedRandom}
      />
    </div>
  );
}
