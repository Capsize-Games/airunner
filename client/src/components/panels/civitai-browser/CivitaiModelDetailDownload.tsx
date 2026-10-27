import { useState } from "react";
import { useDownloadProgress } from "../../downloads/DownloadProgress";
import { useDownloads, type DownloadJob } from "../../downloads/useDownloadState";
import { type CivitaiFile } from "./CivitaiModelDetailTypes";

/**
 * Renders Download, Cancel, or Downloaded depending on file status.
 */
export function DownloadButton({
  selectedFile,
  downloads,
  onDownloadClick,
  onCancel,
}: {
  selectedFile: CivitaiFile | null;
  downloads: DownloadJob[];
  onDownloadClick: () => void;
  onCancel: (jobId: string) => void;
}) {
  const { markCompleted, isDownloaded } = useDownloads();
  const downloadUrl = selectedFile?.downloadUrl;

  // Server-reported file existence (authoritative)
  if (selectedFile?.downloaded) {
    return <DownloadedBadge />;
  }

  // localStorage completion history (secondary)
  if (downloadUrl && isDownloaded(downloadUrl)) {
    return <DownloadedBadge />;
  }

  // Active download in progress
  const match = downloadUrl
    ? downloads.find((d) => d.downloadUrl === downloadUrl)
    : null;
  if (match) {
    return (
      <DownloadStatusButton
        jobId={match.jobId}
        onCancel={() => onCancel(match.jobId)}
        checkDone={() => markCompleted(downloadUrl ?? "")}
      />
    );
  }

  return (
    <button
      className="modal-primary-btn"
      onClick={onDownloadClick}
      disabled={!selectedFile?.downloadUrl}
    >
      Download
    </button>
  );
}

function DownloadedBadge() {
  return <div className="modal-downloaded-badge">Downloaded</div>;
}

function DownloadStatusButton({
  jobId,
  onCancel,
  checkDone,
}: {
  jobId: string;
  onCancel: () => void;
  checkDone: () => void;
}) {
  const state = useDownloadProgress(jobId);
  if (state.status === "completed") {
    setTimeout(() => checkDone(), 0);
    return <DownloadedBadge />;
  }
  return (
    <button className="modal-cancel-btn" onClick={onCancel}>
      Cancel
    </button>
  );
}

/**
 * Overlay prompt for entering a CivitAI API key.
 */
export function ApiKeyPrompt({
  onSubmit,
  onCancel,
}: {
  onSubmit: (key: string) => void;
  onCancel: () => void;
}) {
  const [apiKey, setApiKey] = useState("");

  const handleSubmit = () => {
    const trimmed = apiKey.trim();
    if (!trimmed) return;
    // Stored in sessionStorage (cleared on tab close) rather than
    // localStorage to limit exposure of the API key.
    sessionStorage.setItem("airunner_civitai_api_key", trimmed);
    onSubmit(trimmed);
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        zIndex: 1200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: "var(--theme-bg, #1a1a2e)",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: 6,
          padding: 24,
          maxWidth: 400,
          width: "90%",
          color: "#ccc",
          fontSize: 13,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h4 style={{ margin: "0 0 8px", color: "#fff", fontSize: 15 }}>
          CivitAI API Key Required
        </h4>
        <p style={{ margin: "0 0 12px", fontSize: 12, color: "#999", lineHeight: 1.4 }}>
          A CivitAI API key is needed to download this file.
          You can get one from your CivitAI account settings.
          It will be stored in your browser for future downloads.
        </p>
        <input
          type="password"
          placeholder="Enter your CivitAI API key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
          autoFocus
          style={{
            width: "100%",
            padding: "8px 10px",
            borderRadius: 4,
            border: "1px solid rgba(255,255,255,0.2)",
            background: "rgba(255,255,255,0.08)",
            color: "#fff",
            fontSize: 13,
            outline: "none",
            boxSizing: "border-box",
          }}
        />
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button
            className="modal-primary-btn"
            onClick={handleSubmit}
            disabled={!apiKey.trim()}
          >
            Submit &amp; Download
          </button>
          <button className="modal-secondary-btn" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
