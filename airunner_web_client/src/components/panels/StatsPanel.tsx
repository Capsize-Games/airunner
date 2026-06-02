import { useState, useEffect } from "react";
import {
  getHardwareProfile,
  getSingleton,
} from "../../api/client";
import type { HardwareProfile, ResourceRecord } from "../../types/api";
import ProgressBar from "react-bootstrap/ProgressBar";

export default function StatsPanel() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);
  const [modelNames, setModelNames] = useState<string[]>([]);

  useEffect(() => {
    getHardwareProfile().then(setHw).catch(() => {});
    const timer = setInterval(() => {
      getHardwareProfile().then(setHw).catch(() => {});
    }, 5000);

    // Query active loaded models from the settings domain
    getSingleton("ModelStatus")
      .then((r: ResourceRecord) => {
        const names: string[] = [];
        for (const [key, val] of Object.entries(r)) {
          if (typeof val === "string" && val.trim()) {
            names.push(`${key}: ${val}`);
          }
        }
        setModelNames(names.length > 0 ? names : ["No models loaded"]);
      })
      .catch(() => setModelNames(["Status unavailable"]));

    return () => clearInterval(timer);
  }, []);

  if (!hw) {
    return (
      <div className="p-2">
        <h6 className="text-muted mb-2">Model Resources</h6>
        <p className="text-muted small">Hardware info unavailable.</p>
      </div>
    );
  }

  const vramPct =
    hw.total_vram_gb > 0
      ? ((hw.total_vram_gb - hw.available_vram_gb) /
          hw.total_vram_gb) *
        100
      : 0;
  const ramPct =
    hw.total_ram_gb > 0
      ? ((hw.total_ram_gb - hw.available_ram_gb) /
          hw.total_ram_gb) *
        100
      : 0;

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Model Resources</h6>

      {/* Device info */}
      <div className="small text-muted mb-2">
        {hw.device_name ?? "CPU"} &middot; {hw.cpu_count} cores
      </div>

      {/* VRAM bar */}
      <div className="mb-2">
        <small className="text-muted">VRAM</small>
        <ProgressBar
          now={Math.min(vramPct, 100)}
          variant={vramPct > 90 ? "danger" : "success"}
          className="mt-1"
          style={{ height: 8 }}
        />
        <small className="text-muted">
          {hw.available_vram_gb.toFixed(1)} /{" "}
          {hw.total_vram_gb.toFixed(1)} GB
        </small>
      </div>

      {/* RAM bar */}
      <div className="mb-2">
        <small className="text-muted">RAM</small>
        <ProgressBar
          now={Math.min(ramPct, 100)}
          variant={ramPct > 90 ? "danger" : "info"}
          className="mt-1"
          style={{ height: 8 }}
        />
        <small className="text-muted">
          {hw.available_ram_gb.toFixed(1)} /{" "}
          {hw.total_ram_gb.toFixed(1)} GB
        </small>
      </div>

      {/* Loaded models */}
      <hr className="border-secondary" />
      <small className="text-muted fw-bold">Loaded Models</small>
      <ul className="list-unstyled small text-muted mt-1 mb-0">
        {modelNames.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
    </div>
  );
}
