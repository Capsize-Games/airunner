import { useState } from "react";
import DownloadProgress from "./DownloadProgress";
import { useDownloads, type DownloadJob } from "./useDownloadState";
import { cancelDownloadJob, startCivitaiFileDownload } from "../../api/downloads";

export default function DownloadTray() {
  const { downloads, addDownload, removeDownload, clearDownloads } = useDownloads();
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
    // Remove the interrupted entry
    removeDownload(job.jobId);
    // Re-submit the download
    try {
      const result = await startCivitaiFileDownload({
        url: job.downloadUrl,
        output_path: `/tmp/airunner/downloads/${job.label}`,
        api_key: localStorage.getItem("airunner_civitai_api_key") ?? "",
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
        <span>Downloads ({downloads.length})</span>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={clearDownloads}
            style={{
              background: "transparent",
              border: "none",
              color: "#888",
              cursor: "pointer",
              fontSize: 10,
              padding: 0,
            }}
          >
            Clear all
          </button>
          <button
            onClick={handleClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#888",
              cursor: "pointer",
              fontSize: 14,
              padding: 0,
              lineHeight: 1,
            }}
            title="Close tray"
          >
            ✕
          </button>
        </div>
      </div>
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
          <div style={{ flex: 1, minWidth: 0 }}>
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
            <button
              onClick={() => handleResume(job)}
              style={{
                background: "rgba(255,255,255,0.12)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: 3,
                color: "#ccc",
                cursor: "pointer",
                fontSize: 10,
                padding: "2px 8px",
                whiteSpace: "nowrap",
              }}
            >
              Resume
            </button>
            <button
              onClick={() => handleCancel(job)}
              style={{
                background: "rgba(255,80,80,0.15)",
                border: "1px solid rgba(255,80,80,0.25)",
                borderRadius: 3,
                color: "#ff8888",
                cursor: "pointer",
                fontSize: 10,
                padding: "2px 8px",
                whiteSpace: "nowrap",
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
