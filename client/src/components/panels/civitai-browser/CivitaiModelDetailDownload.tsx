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
      onClick={onDownloadClick}
      disabled={!selectedFile?.downloadUrl}
      style={{
        flex: 1,
        padding: "6px 12px",
        background: selectedFile?.downloadUrl
          ? "rgba(255,255,255,0.2)"
          : "rgba(255,255,255,0.1)",
        border: "1px solid rgba(255,255,255,0.2)",
        borderRadius: 4,
        color: selectedFile?.downloadUrl ? "#fff" : "#666",
        cursor: selectedFile?.downloadUrl ? "pointer" : "default",
        fontSize: 12,
      }}
    >
      Download
    </button>
  );
}

function DownloadedBadge() {
  return (
    <div
      style={{
        flex: 1,
        padding: "6px 12px",
        borderRadius: 4,
        background: "rgba(0,200,100,0.15)",
        border: "1px solid rgba(0,200,100,0.25)",
        color: "#66ddaa",
        fontSize: 12,
        textAlign: "center",
      }}
    >
      Downloaded
    </div>
  );
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
    <button
      onClick={onCancel}
      style={{
        flex: 1,
        padding: "6px 12px",
        background: "rgba(255,80,80,0.2)",
        border: "1px solid rgba(255,80,80,0.3)",
        borderRadius: 4,
        color: "#ff8888",
        cursor: "pointer",
        fontSize: 12,
      }}
    >
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
    localStorage.setItem("airunner_civitai_api_key", trimmed);
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
            onClick={handleSubmit}
            disabled={!apiKey.trim()}
            style={{
              flex: 1,
              padding: "7px 12px",
              background: apiKey.trim() ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: 4,
              color: apiKey.trim() ? "#fff" : "#666",
              cursor: apiKey.trim() ? "pointer" : "default",
              fontSize: 12,
            }}
          >
            Submit & Download
          </button>
          <button
            onClick={onCancel}
            style={{
              flexShrink: 0,
              padding: "7px 12px",
              background: "transparent",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: 4,
              color: "#888",
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
