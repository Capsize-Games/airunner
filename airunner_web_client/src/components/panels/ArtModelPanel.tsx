import { useState, useEffect } from "react";
import {
  getSingleton,
  updateSingleton,
  getBootstrap,
  getArtOptions,
  listLLMModels,
} from "../../api/client";
import type { ResourceRecord } from "../../types/api";
import Form from "react-bootstrap/Form";
import ProgressBar from "react-bootstrap/ProgressBar";

interface OptionItem {
  label: string;
  value: string;
}

export default function ArtModelPanel() {
  const [version, setVersion] = useState("");
  const [scheduler, setScheduler] = useState("");
  const [precision, setPrecision] = useState("");
  const [versions, setVersions] = useState<OptionItem[]>([]);
  const [schedulers, setSchedulers] = useState<OptionItem[]>([]);
  const [precisions, setPrecisions] = useState<OptionItem[]>([]);
  // Sampler controls
  const [nSamples, setNSamples] = useState(1);
  const [imagesPerBatch, setImagesPerBatch] = useState(1);
  const [steps, setSteps] = useState(20);
  const [cfgScale, setCfgScale] = useState(7.5);
  const [width, setWidth] = useState(1024);
  const [height, setHeight] = useState(1024);
  const [seed, setSeed] = useState(0);
  const [vramEstimate, setVramEstimate] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getArtOptions()
      .then((opts) => {
        setSchedulers(opts.schedulers ?? []);
        setPrecisions(opts.precisions ?? []);
      })
      .catch(() => {});

    getBootstrap()
      .then((data) => {
        const seen = new Map<string, string>();
        for (const p of data.pipelines ?? []) {
          const v = String(p.version ?? "");
          if (v && !seen.has(v)) seen.set(v, v);
        }
        const unique: OptionItem[] = [];
        for (const v of seen.values()) unique.push({ label: v, value: v });
        setVersions(unique);
      })
      .catch(() => {});

    getSingleton("GeneratorSettings")
      .then((r: ResourceRecord) => {
        setVersion(String(r.version ?? ""));
        setScheduler(String(r.scheduler ?? ""));
        setPrecision(String(r.dtype ?? ""));
        setNSamples(Number(r.n_samples ?? 1));
        setImagesPerBatch(Number(r.images_per_batch ?? 1));
        setSteps(Number(r.steps ?? 20));
        setCfgScale(Number(r.cfg_scale ?? 7.5));
        setWidth(Number(r.width ?? 1024));
        setHeight(Number(r.height ?? 1024));
        setSeed(Number(r.seed ?? 0));
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    getSingleton("VRAMEstimate")
      .then((r: ResourceRecord) => {
        const gb = Number(r.file_size_gb ?? 0);
        if (gb > 0) setVramEstimate(gb);
      })
      .catch(() => {});
  }, []);

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("GeneratorSettings", updates).catch(() => {});
  };

  if (loading) {
    return <div className="p-2 small" style={{ color: "#a0a0a8" }}>Loading...</div>;
  }

  return (
    <div className="p-2">
      <h6 style={{ color: "#a0a0a8" }} className="mb-2">Art Model</h6>

      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>Version</Form.Label>
        <Form.Select
          size="sm"
          value={version}
          onChange={(e) => { setVersion(e.target.value); persist({ version: e.target.value }); }}
        >
          <option value="">Select version...</option>
          {versions.map((v) => (
            <option key={v.value} value={v.value}>{v.label}</option>
          ))}
        </Form.Select>
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>Scheduler</Form.Label>
        <Form.Select
          size="sm"
          value={scheduler}
          onChange={(e) => { setScheduler(e.target.value); persist({ scheduler: e.target.value }); }}
        >
          <option value="">Select scheduler...</option>
          {schedulers.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </Form.Select>
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>Precision</Form.Label>
        <Form.Select
          size="sm"
          value={precision}
          onChange={(e) => { setPrecision(e.target.value); persist({ dtype: e.target.value }); }}
        >
          <option value="">Select precision...</option>
          {precisions.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
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
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Samples</Form.Label>
          <Form.Control
            type="number" size="sm" min={1} max={1000}
            value={nSamples}
            onChange={(e) => { const v = Number(e.target.value); setNSamples(v); persist({ n_samples: v }); }}
          />
        </div>
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Batch</Form.Label>
          <Form.Control
            type="number" size="sm" min={1} max={6}
            value={imagesPerBatch}
            onChange={(e) => { const v = Number(e.target.value); setImagesPerBatch(v); persist({ images_per_batch: v }); }}
          />
        </div>
      </div>
      <div className="row g-2 mb-2">
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Steps</Form.Label>
          <Form.Control
            type="number" size="sm" min={1} max={150}
            value={steps}
            onChange={(e) => { const v = Number(e.target.value); setSteps(v); persist({ steps: v }); }}
          />
        </div>
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>
            CFG ({cfgScale.toFixed(1)})
          </Form.Label>
          <Form.Range
            min={1} max={30} step={0.5}
            value={cfgScale}
            onChange={(e) => { const v = Number(e.target.value); setCfgScale(v); persist({ cfg_scale: v }); }}
          />
        </div>
      </div>
      <div className="row g-2 mb-2">
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Width</Form.Label>
          <Form.Control
            type="number" size="sm" min={64} max={4096} step={64}
            value={width}
            onChange={(e) => { const v = Number(e.target.value); setWidth(v); persist({ width: v }); }}
          />
        </div>
        <div className="col-6">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Height</Form.Label>
          <Form.Control
            type="number" size="sm" min={64} max={4096} step={64}
            value={height}
            onChange={(e) => { const v = Number(e.target.value); setHeight(v); persist({ height: v }); }}
          />
        </div>
      </div>
      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>Seed (0=random)</Form.Label>
        <Form.Control
          type="number" size="sm"
          value={seed}
          onChange={(e) => { const v = Number(e.target.value); setSeed(v); persist({ seed: v }); }}
        />
      </Form.Group>
    </div>
  );
}
