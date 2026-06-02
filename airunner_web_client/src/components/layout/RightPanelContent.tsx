import { useState, useEffect } from "react";
import {
  getSingleton,
  getHardwareProfile,
} from "../../api/client";
import type { HardwareProfile, ResourceRecord } from "../../types/api";
import Form from "react-bootstrap/Form";
import ProgressBar from "react-bootstrap/ProgressBar";

// ── Art Model ──
export function ArtModelPanel() {
  const [version, setVersion] = useState("SDXL 1.0");
  const [scheduler, setScheduler] = useState("euler_a");
  const [precision, setPrecision] = useState("bfloat16");

  useEffect(() => {
    getSingleton("GeneratorSettings")
      .then((r: ResourceRecord) => {
        setVersion(String(r.version ?? "SDXL 1.0"));
        setScheduler(String(r.scheduler ?? "EulerAncestralDiscrete"));
        setPrecision(String(r.dtype ?? "bfloat16"));
      })
      .catch(() => {});
  }, []);

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Art Model</h6>
      <Form.Group className="mb-2">
        <Form.Label className="small text-muted">Version</Form.Label>
        <Form.Select
          size="sm"
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="SDXL 1.0">SDXL 1.0</option>
          <option value="SDXL Turbo">SDXL Turbo</option>
          <option value="Z-Image Turbo">Z-Image Turbo</option>
        </Form.Select>
      </Form.Group>
      <Form.Group className="mb-2">
        <Form.Label className="small text-muted">Scheduler</Form.Label>
        <Form.Select
          size="sm"
          value={scheduler}
          onChange={(e) => setScheduler(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="euler_a">Euler Ancestral</option>
          <option value="euler">Euler</option>
          <option value="dpm_2">DPM 2</option>
          <option value="lms">LMS</option>
        </Form.Select>
      </Form.Group>
      <Form.Group className="mb-2">
        <Form.Label className="small text-muted">
          Precision ({precision})
        </Form.Label>
        <Form.Select
          size="sm"
          value={precision}
          onChange={(e) => setPrecision(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="bfloat16">BF16</option>
          <option value="float16">FP16</option>
          <option value="float32">FP32</option>
          <option value="4bit">4-bit</option>
          <option value="8bit">8-bit</option>
        </Form.Select>
      </Form.Group>
    </div>
  );
}

// ── LoRA ──
export function LoraPanel() {
  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">LoRA</h6>
      <p className="muted-text">
        LoRA models will appear here. Add LoRA files to your models directory.
      </p>
    </div>
  );
}

// ── Embeddings ──
export function EmbeddingsPanel() {
  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Embeddings</h6>
      <p className="muted-text">
        Textual inversion embeddings will appear here.
      </p>
    </div>
  );
}

// ── Layers ──
export function LayersPanel() {
  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Layers</h6>
      <p className="muted-text">
        Canvas layers will appear here.
      </p>
    </div>
  );
}

// ── Grid ──
export function GridPanel() {
  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Grid Settings</h6>
      <Form.Group className="mb-2">
        <Form.Check
          type="switch"
          label="Show Grid"
          defaultChecked
          className="small text-muted"
        />
      </Form.Group>
      <Form.Group className="mb-2">
        <Form.Check
          type="switch"
          label="Snap to Grid"
          defaultChecked
          className="small text-muted"
        />
      </Form.Group>
      <Form.Group className="mb-2">
        <Form.Label className="small text-muted">Grid Size</Form.Label>
        <Form.Control
          size="sm"
          type="number"
          defaultValue={64}
          className="bg-dark text-light border-secondary"
        />
      </Form.Group>
    </div>
  );
}

// ── Image Browser ──
export function ImageBrowserPanel() {
  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Image Browser</h6>
      <p className="muted-text">
        Generated images will appear here. Export to save them.
      </p>
    </div>
  );
}

// ── Stats ──
export function StatsPanel() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);

  useEffect(() => {
    getHardwareProfile().then(setHw).catch(() => {});
    const timer = setInterval(() => {
      getHardwareProfile().then(setHw).catch(() => {});
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  if (!hw) {
    return (
      <div className="p-2">
        <h6 className="text-muted">Model Resources</h6>
        <p className="muted-text">Hardware info unavailable.</p>
      </div>
    );
  }

  const vramPct =
    hw.total_vram_gb > 0
      ? ((hw.total_vram_gb - hw.available_vram_gb) / hw.total_vram_gb) * 100
      : 0;
  const ramPct =
    hw.total_ram_gb > 0
      ? ((hw.total_ram_gb - hw.available_ram_gb) / hw.total_ram_gb) * 100
      : 0;

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Model Resources</h6>
      <div className="small text-muted mb-2">
        {hw.device_name ?? "CPU"} · {hw.cpu_count} cores
      </div>

      <div className="mb-2">
        <small className="text-muted">VRAM</small>
        <ProgressBar
          now={Math.min(vramPct, 100)}
          variant={vramPct > 90 ? "danger" : "success"}
          className="mt-1"
          style={{ height: 8 }}
        />
        <small className="text-muted">
          {hw.available_vram_gb.toFixed(1)} / {hw.total_vram_gb.toFixed(1)} GB
        </small>
      </div>

      <div className="mb-2">
        <small className="text-muted">RAM</small>
        <ProgressBar
          now={Math.min(ramPct, 100)}
          variant={ramPct > 90 ? "danger" : "info"}
          className="mt-1"
          style={{ height: 8 }}
        />
        <small className="text-muted">
          {hw.available_ram_gb.toFixed(1)} / {hw.total_ram_gb.toFixed(1)} GB
        </small>
      </div>
    </div>
  );
}
