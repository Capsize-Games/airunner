import { useState, useEffect } from "react";
import {
  getSingleton,
  updateSingleton,
} from "../../api/client";
import type { ArtOptionsResponse } from "../../api/client";
import Form from "react-bootstrap/Form";
import ProgressBar from "react-bootstrap/ProgressBar";
import SliderWithSpinbox from "./SliderWithSpinbox";

const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

function randomSeed(): number {
  return Math.floor(Math.random() * 2147483647) + 1;
}

const LS_KEY = "airunner_art_settings";

function saveToStorage(key: string, val: number) {
  try {
    const data = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
    data[key] = val;
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  } catch { /* */ }
}

function loadFromStorage(key: string, fallback: number): number {
  try {
    const data = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
    const v = data[key];
    return v !== undefined ? Number(v) : fallback;
  } catch {
    return fallback;
  }
}

export default function ArtModelPanel() {
  const [version, setVersion] = useState("");
  const [modelPath, setModelPath] = useState("");
  const [scheduler, setScheduler] = useState("");
  const [precision, setPrecision] = useState("");

  const [options, setOptions] = useState<ArtOptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Sampler controls — load from localStorage on mount
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

  // Listen for changes from ArtPromptPanel's selector
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
      const s = randomSeed();
      setSeedRandomized(true);
      setSeed(s);
      persist({ seed: -1 });
    }
  };

  return (
    <div className="p-2">
      <div className="d-flex align-items-center gap-2 mb-2">
        <h6 style={{ color: "#a0a0a8" }} className="mb-0">
          Art Model
        </h6>
        {loading && (
          <div
            className="spinner-border spinner-border-sm"
            role="status"
            style={{ color: "#a0a0a8", width: 12, height: 12 }}
          />
        )}
      </div>

      {/* Version */}
      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>
          Version
        </Form.Label>
        <Form.Select
          size="sm"
          value={version}
          disabled={loading}
          onChange={(e) => handleVersionChange(e.target.value)}
        >
          <option value="">Version...</option>
          {(options?.versions ?? []).map((v) => (
            <option key={v.name} value={v.name}>
              {v.name}
            </option>
          ))}
        </Form.Select>
      </Form.Group>

      {/* Model */}
      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>
          Model
        </Form.Label>
        <Form.Select
          size="sm"
          value={modelPath}
          disabled={loading || !version || availableModels.length === 0}
          onChange={(e) => handleModelChange(e.target.value)}
        >
          <option value="">
            {!version ? "Version..." : "Model..."}
          </option>
          {availableModels.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </Form.Select>
      </Form.Group>

      {/* Scheduler */}
      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>
          Scheduler
        </Form.Label>
        <Form.Select
          size="sm"
          value={scheduler}
          disabled={loading}
          onChange={(e) => {
            setScheduler(e.target.value);
            persist({ scheduler: e.target.value });
          }}
        >
          <option value="">Select scheduler...</option>
          {availableSchedulers.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </Form.Select>
      </Form.Group>

      {/* Precision */}
      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>
          Precision
        </Form.Label>
        <Form.Select
          size="sm"
          value={precision}
          disabled={loading}
          onChange={(e) => {
            setPrecision(e.target.value);
            persist({ dtype: e.target.value });
          }}
        >
          <option value="">Select precision...</option>
          {precisions.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </Form.Select>
      </Form.Group>

      {vramEstimate !== null && (
        <div className="mt-2 mb-2">
          <small style={{ color: "#a0a0a8" }}>
            Estimated VRAM: {vramEstimate.toFixed(1)} GB
          </small>
          <ProgressBar
            now={Math.min((vramEstimate / 24) * 100, 100)}
            variant={vramEstimate > 20 ? "danger" : "success"}
            className="mt-1"
            style={{ height: 6 }}
          />
        </div>
      )}

      <hr className="border-secondary" />

      {/* Sampler controls — stacked vertically */}
      <SliderWithSpinbox
        label="Samples"
        value={nSamples}
        min={1}
        max={1000}
        step={1}
        defaultValue={1}
        onChange={(v) => { setNSamples(v); saveToStorage("n_samples", v); persist({ n_samples: v }); }}
      />
      <SliderWithSpinbox
        label="Batch"
        value={imagesPerBatch}
        min={1}
        max={6}
        step={1}
        defaultValue={1}
        onChange={(v) => { setImagesPerBatch(v); saveToStorage("images_per_batch", v); persist({ images_per_batch: v }); }}
      />
      <SliderWithSpinbox
        label="Steps"
        value={steps}
        min={1}
        max={150}
        step={1}
        defaultValue={20}
        onChange={(v) => { setSteps(v); saveToStorage("steps", v); persist({ steps: v }); }}
      />
      <SliderWithSpinbox
        label="CFG"
        value={cfgScale}
        min={1}
        max={30}
        step={0.5}
        displayAsFloat
        defaultValue={7.5}
        onChange={(v) => { setCfgScale(v); saveToStorage("cfg_scale", v); persist({ cfg_scale: v }); }}
      />
      <SliderWithSpinbox
        label="Width"
        value={width}
        min={64}
        max={4096}
        step={64}
        defaultValue={1024}
        onChange={(v) => { setWidth(v); saveToStorage("width", v); persist({ width: v }); }}
      />
      <SliderWithSpinbox
        label="Height"
        value={height}
        min={64}
        max={4096}
        step={64}
        defaultValue={1024}
        onChange={(v) => { setHeight(v); saveToStorage("height", v); persist({ height: v }); }}
      />

      {/* Seed */}
      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>
          Seed
        </Form.Label>
        <div className="d-flex gap-2 align-items-center">
          <Form.Control
            size="sm"
            value={seed}
            readOnly={seedRandomized}
            disabled={loading}
            style={{
              flex: 1,
              background: "#1a1a2e",
              color: seedRandomized ? "#666" : "#c8c8c8",
              borderColor: seedRandomized ? "#555" : "#333",
              opacity: seedRandomized ? 0.5 : 1,
            }}
            onChange={(e) => {
              const raw = e.target.value.replace(/[^0-9\-]/g, "");
              if (raw === "") return;
              const v = Number(raw);
              if (isNaN(v)) return;
              setSeed(v);
              setSeedRandomized(false);
              persist({ seed: v });
            }}
          />
          <button
            type="button"
            className="btn btn-sm p-1"
            onClick={toggleSeedRandom}
            title={
              seedRandomized
                ? "Use a fixed seed"
                : "Randomize seed on each generation"
            }
            style={{
              background: seedRandomized
                ? "var(--bs-primary)"
                : "transparent",
              border: "1px solid #444",
              borderRadius: 4,
              minWidth: 30,
              height: 30,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <img
              src={icon("dices")}
              alt="Randomize"
              style={{
                width: 16,
                height: 16,
                filter: seedRandomized ? "invert(1)" : "invert(0.6)",
              }}
            />
          </button>
        </div>
      </Form.Group>
    </div>
  );
}
