import { useState, useEffect, useCallback } from "react";
import ProgressBar from "react-bootstrap/ProgressBar";
import { getHardwareProfile, BASE_URL } from "../../api/client";
import type { HardwareProfile } from "../../types/api";
import type { ActiveModelInfo } from "../../api/client";

export default function StatsPanel() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);
  const [models, setModels] = useState<ActiveModelInfo[]>([]);

  const fetchActiveModels = useCallback(async () => {
    try {
      const { listActiveModels } = await import("../../api/client");
      const resp = await listActiveModels();
      setModels(resp.models ?? []);
    } catch {
      // endpoint may be unavailable
    }
  }, []);

  useEffect(() => {
    getHardwareProfile().then(setHw).catch(() => {});
    const timer = setInterval(() => {
      getHardwareProfile().then(setHw).catch(() => {});
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  // Poll active models
  useEffect(() => {
    fetchActiveModels();
    const timer = setInterval(fetchActiveModels, 3000);
    return () => clearInterval(timer);
  }, [fetchActiveModels]);

  // Listen for live model-status SSE events
  useEffect(() => {
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/models/status`,
    );
    eventSource.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "model_status") {
          // Refresh the model list immediately when a status changes
          fetchActiveModels();
        }
      } catch { /* ignore malformed */ }
    });
    eventSource.onerror = () => {
      // auto-reconnect
    };
    return () => {
      eventSource.close();
    };
  }, [fetchActiveModels]);

  const handleUnload = async (m: ActiveModelInfo) => {
    try {
      const { unloadModel } = await import("../../api/client");
      await unloadModel(m.model_id, m.model_type);
      fetchActiveModels();
    } catch {
      // ignore
    }
  };

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

      {/* Loaded models list */}
      {models.length > 0 && (
        <div className="mt-2">
          <small className="text-muted d-block mb-1">
            Loaded Models
          </small>
          {models.map((m) => (
            <div
              key={m.model_id}
              className="d-flex align-items-center justify-content-between mb-1"
              style={{ fontSize: "11px" }}
            >
              <span className="text-truncate" style={{ maxWidth: 140 }}>
                <span
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    backgroundColor:
                      m.status === "loaded"
                        ? "var(--bs-success)"
                        : m.status === "loading"
                          ? "var(--bs-warning)"
                          : "var(--bs-danger)",
                    marginRight: 4,
                    flexShrink: 0,
                  }}
                />
                {m.name || m.model_type}
              </span>
              {m.can_unload && (
                <button
                  onClick={() => handleUnload(m)}
                  style={{
                    background: "transparent",
                    border: "1px solid #555",
                    borderRadius: 3,
                    color: "#aaa",
                    cursor: "pointer",
                    fontSize: 10,
                    padding: "0 4px",
                    lineHeight: "16px",
                    flexShrink: 0,
                  }}
                  title={`Unload ${m.name || m.model_type}`}
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
