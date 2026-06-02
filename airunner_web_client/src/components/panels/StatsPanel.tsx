import { useState, useEffect } from "react";
import { getHardwareProfile } from "../../api/client";
import type { HardwareProfile } from "../../types/api";
import ProgressBar from "react-bootstrap/ProgressBar";

export default function StatsPanel() {
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
        <h6 className="text-muted mb-2">Model Resources</h6>
        <p className="text-muted small">
          Hardware info unavailable.
        </p>
      </div>
    );
  }

  const vramUsed =
    hw.total_vram_gb > 0
      ? hw.total_vram_gb - hw.available_vram_gb
      : 0;
  const vramPct =
    hw.total_vram_gb > 0
      ? (vramUsed / hw.total_vram_gb) * 100
      : 0;
  const ramUsed =
    hw.total_ram_gb > 0
      ? hw.total_ram_gb - hw.available_ram_gb
      : 0;
  const ramPct =
    hw.total_ram_gb > 0
      ? (ramUsed / hw.total_ram_gb) * 100
      : 0;

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Model Resources</h6>

      <div className="small text-muted mb-2">
        {hw.device_name ?? "CPU"} &middot; {hw.cpu_count}{" "}
        cores
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
          {vramUsed.toFixed(1)} /{" "}
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
          {ramUsed.toFixed(1)} /{" "}
          {hw.total_ram_gb.toFixed(1)} GB
        </small>
      </div>
    </div>
  );
}
