import { useState, useEffect, useRef } from "react";
import { BASE_URL } from "../../types/api";
import DownloadProgress, { useDownloadProgress } from "./DownloadProgress";
import { useDownloads, type DownloadJob } from "./useDownloadState";
import { cancelDownloadJob, startCivitaiFileDownload } from "../../api/downloads";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_DOWNLOADS } from "../../features/events/types";

export default function DownloadTray() {
  const { downloads, addDownload, removeDownload, clearDownloads } = useDownloads();
  const startedRef = useRef<Set<string>>(new Set());

  // Listen for auto-triggered model downloads arriving over the events
  // WebSocket.  When inference finds a missing model the server starts a
  // tracked job and broadcasts a "started" event carrying the jobId.
  useEventBus([EVENT_DOWNLOADS], (_event, data) => {
    const payload = data as {
      type?: string;
      job_id?: string;
      repo_id?: string;
      model_name?: string;
      model_type?: string;
      started_at?: string;
      error?: string;
    };

    if (payload.type === "started" && payload.job_id) {
      if (startedRef.current.has(payload.job_id)) return;
      startedRef.current.add(payload.job_id);
      addDownload({
        jobId: payload.job_id,
        label: payload.model_name || payload.repo_id || "Model Download",
        modelName: payload.model_name,
        modelType: payload.model_type,
        startedAt: payload.started_at || new Date().toISOString(),
      });
    }
  });
  const [visible, setVisible] = useState(() => {
    try {
      return localStorage.getItem("airunner_download_tray_visible") !== "false";
    } catch {
      return true;
    }
  });

  const handleClose = () => {
    setVisible(false);
    try {
      localStorage.setItem("airunner_download_tray_visible", "false");
    } catch { /* */ }
  };

  const handleCancel = async (job: DownloadJob) => {
    try {
      await cancelDownloadJob(job.jobId);
    } catch { /* */ }
    removeDownload(job.jobId);
  };

  const handleResume = async (job: DownloadJob) => {
    if (!job.downloadUrl) return;
    removeDownload(job.jobId);
    try {
      const result = await startCivitaiFileDownload({
        url: job.downloadUrl,
        output_path: `/tmp/airunner/downloads/${job.label}`,
        api_key: localStorage.getItem("airunner_civitai_api_key") ?? "",
        base_model: job.baseModel,
        model_type: job.modelType,
      });
      if (result.job_id) {
        addDownload({
          ...job,
          jobId: result.job_id,
          startedAt: new Date().toISOString(),
        });
      }
    } catch { /* */ }
  };

  if (!visible || downloads.length === 0) return null;

  return (
    <div
      style={{
        borderTop: "1px solid rgba(255,255,255,0.12)",
        background: "var(--theme-bg, #1a1a2e)",
        maxHeight: 200,
        overflowY: "auto",
      }}
    >
      <TrayHeader
        count={downloads.length}
        jobIds={downloads.map((d) => d.jobId)}
        onClearAll={clearDownloads}
        onClose={handleClose}
      />
      {downloads.map((job) => (
        <div
          key={job.jobId}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "4px 12px",
            fontSize: 11,
          }}
        >
          <div className="flex-grow-1 min-w-0">
            <div className="text-truncate" style={{ color: "#ccc" }}>
              {job.modelName || job.label}
            </div>
            <div style={{ fontSize: 10, color: "#666" }}>
              {[job.baseModel, job.modelType].filter(Boolean).join(" · ")}
            </div>
          </div>
          <div style={{ flex: "0 0 180px" }}>
            <DownloadProgress
              jobId={job.jobId}
              onNotFound={() => removeDownload(job.jobId)}
            />
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            <ResumeButton jobId={job.jobId} onResume={() => handleResume(job)} />
            <CancelButton jobId={job.jobId} onCancel={() => handleCancel(job)} />
          </div>
        </div>
      ))}
    </div>
  );
}

function TrayHeader({
  count,
  jobIds,
  onClearAll,
  onClose,
}: {
  count: number;
  jobIds: string[];
  onClearAll: () => void;
  onClose: () => void;
}) {
  const [anyActive, setAnyActive] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const terminal = new Set<string>();

    const check = async () => {
      const results = await Promise.all(
        jobIds.map(async (id: string) => {
          if (terminal.has(id)) return false;
          try {
            const res = await fetch(`${BASE_URL}/api/v1/downloads/status/${id}`);
            if (!res.ok) { terminal.add(id); return false; }
            const job = await res.json();
            if (job.status !== "running" && job.status !== "interrupted") {
              terminal.add(id);
            }
            return job.status === "running" || job.status === "interrupted";
          } catch {
            return false;
          }
        }),
      );
      const active = results.some(Boolean);
      if (!cancelled) setAnyActive(active);
      if (terminal.size === jobIds.length) return;
      setTimeout(check, 2000);
    };
    check();
    return () => { cancelled = true; };
  }, [jobIds]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "4px 12px",
        fontSize: 11,
        color: "#888",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      <span>Downloads ({count})</span>
      {!anyActive && (
        <div style={{ display: "flex", gap: 8 }}>
          <button className="tray-text-btn" onClick={onClearAll}>
            Clear all
          </button>
          <button className="tray-text-btn tray-text-btn-lg" onClick={onClose} title="Close tray">
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

function ResumeButton({ jobId, onResume }: { jobId: string; onResume: () => void }) {
  const state = useDownloadProgress(jobId);
  if (state.status !== "interrupted") return null;
  return (
    <button className="download-resume-btn" onClick={onResume}>
      Resume
    </button>
  );
}

function CancelButton({ jobId, onCancel }: { jobId: string; onCancel: () => void }) {
  const state = useDownloadProgress(jobId);
  if (state.status !== "running" && state.status !== "interrupted") return null;
  return (
    <button className="download-cancel-btn" onClick={onCancel}>
      Cancel
    </button>
  );
}
