import { useState, useEffect } from "react";
import {
  getSingleton,
  updateSingleton,
} from "../../api/client";
import type { ArtOptionsResponse } from "../../api/client";
import Form from "react-bootstrap/Form";
import ProgressBar from "react-bootstrap/ProgressBar";

export default function ArtModelPanel() {
  const [version, setVersion] = useState("");
  const [modelPath, setModelPath] = useState("");
  const [scheduler, setScheduler] = useState("");
  const [precision, setPrecision] = useState("");

  const [options, setOptions] = useState<ArtOptionsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Sampler controls
  const [nSamples, setNSamples] = useState(1);
  const [imagesPerBatch, setImagesPerBatch] = useState(1);
  const [steps, setSteps] = useState(20);
  const [cfgScale, setCfgScale] = useState(7.5);
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);
  const [seed, setSeed] = useState(0);
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
        setNSamples(Number(r.n_samples ?? 1));
        setImagesPerBatch(Number(r.images_per_batch ?? 1));
        setSteps(Number(r.steps ?? 20));
        setCfgScale(Number(r.cfg_scale ?? 7.5));
        setWidth(Number(r.width ?? 1024));
        setHeight(Number(r.height ?? 1024));
        setSeed(Number(r.seed ?? 0));
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
    window.dispatchEvent(new CustomEvent("art-model-changed", { detail: m }));
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
            {!version
              ? "Version..."
              : "Model..."}
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

      {/* Sampler controls */}
      <div className="row g-2 mb-2">
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>
            Samples
          </Form.Label>
          <Form.Control
            type="number"
            size="sm"
            min={1}
            max={1000}
            value={nSamples}
            disabled={loading}
            onChange={(e) => {
              const v = Number(e.target.value);
              setNSamples(v);
              persist({ n_samples: v });
            }}
          />
        </div>
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>
            Batch
          </Form.Label>
          <Form.Control
            type="number"
            size="sm"
            min={1}
            max={6}
            value={imagesPerBatch}
            disabled={loading}
            onChange={(e) => {
              const v = Number(e.target.value);
              setImagesPerBatch(v);
              persist({ images_per_batch: v });
            }}
          />
        </div>
      </div>
      <div className="row g-2 mb-2">
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>
            Steps
          </Form.Label>
          <Form.Control
            type="number"
            size="sm"
            min={1}
            max={150}
            value={steps}
            disabled={loading}
            onChange={(e) => {
              const v = Number(e.target.value);
              setSteps(v);
              persist({ steps: v });
            }}
          />
        </div>
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>
            CFG ({cfgScale.toFixed(1)})
          </Form.Label>
          <Form.Range
            min={1}
            max={30}
            step={0.5}
            value={cfgScale}
            disabled={loading}
            onChange={(e) => {
              const v = Number(e.target.value);
              setCfgScale(v);
              persist({ cfg_scale: v });
            }}
          />
        </div>
      </div>
      <div className="row g-2 mb-2">
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>
            Width
          </Form.Label>
          <Form.Control
            type="number"
            size="sm"
            min={64}
            max={4096}
            step={64}
            value={width}
            disabled={loading}
            onChange={(e) => {
              const v = Number(e.target.value);
              setWidth(v);
              persist({ width: v });
            }}
          />
        </div>
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>
            Height
          </Form.Label>
          <Form.Control
            type="number"
            size="sm"
            min={64}
            max={4096}
            step={64}
            value={height}
            disabled={loading}
            onChange={(e) => {
              const v = Number(e.target.value);
              setHeight(v);
              persist({ height: v });
            }}
          />
        </div>
      </div>
      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>
          Seed (0=random)
        </Form.Label>
        <Form.Control
          type="number"
          size="sm"
          value={seed}
          disabled={loading}
          onChange={(e) => {
            const v = Number(e.target.value);
            setSeed(v);
            persist({ seed: v });
          }}
        />
      </Form.Group>
    </div>
  );
}
