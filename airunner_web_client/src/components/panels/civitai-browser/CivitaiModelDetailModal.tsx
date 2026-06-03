import { useEffect, useCallback, useState, useRef } from "react";
import { BASE_URL } from "../../../types/api";
import CivitaiImage from "./CivitaiImage";
import DownloadProgress, { useDownloadProgress } from "../../downloads/DownloadProgress";
import { startCivitaiFileDownload, cancelDownloadJob } from "../../../api/downloads";
import { useDownloads, type DownloadJob } from "../../downloads/useDownloadState";
import type { JsonObject } from "../../../types/api";

interface VersionImage {
  url: string;
  nsfw?: string;
  width?: number;
  height?: number;
  /** Inline base64 images from the server, keyed by size. */
  images_base64?: Record<string, string>;
}

interface CivitaiVersion {
  id: number;
  name: string;
  baseModel?: string;
  files?: CivitaiFile[];
  images?: VersionImage[];
  downloadUrl?: string;
}

interface CivitaiFile {
  id: number;
  name: string;
  sizeKB?: number;
  downloadUrl?: string;
  /** Server sets this to true when the file already exists on disk. */
  downloaded?: boolean;
}

interface ModelDetailData {
  id: number;
  name: string;
  description?: string;
  creator?: string;
  type?: string;
  stats?: { downloadCount?: number; favoriteCount?: number; commentCount?: number };
  versions?: CivitaiVersion[];
  allowNoCredit?: boolean;
  allowCommercialUse?: string;
  allowDerivatives?: string;
  allowDifferentLicense?: boolean;
}

interface CivitaiModelDetailModalProps {
  model: ModelDetailData | null;
  onClose: () => void;
  loading?: boolean;
  /** Current base model filter (e.g. "SDXL 1.0") for download metadata. */
  baseModel?: string;
  /** Current model type filter (e.g. "Checkpoint") for download metadata. */
  modelType?: string;
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, "").trim();
}



export default function CivitaiModelDetailModal({
  model,
  onClose,
  loading,
  baseModel: currentBaseModel,
  modelType: currentModelType,
}: CivitaiModelDetailModalProps) {
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [previewBase64, setPreviewBase64] = useState<string>("");
  const { downloads, addDownload, removeDownload, isDownloaded } = useDownloads();
  const [showApiKeyPrompt, setShowApiKeyPrompt] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [pendingDownloadUrl, setPendingDownloadUrl] = useState<string | null>(null);
  const [pendingFileName, setPendingFileName] = useState<string>("");

  const versions = model?.versions ?? [];

  // Auto-select first version
  useEffect(() => {
    if (versions.length > 0) {
      setSelectedVersionId(versions[0].id);
      const files = versions[0].files ?? [];
      setSelectedFileId(files.length > 0 ? files[0].id : null);
      const images = versions[0].images ?? [];
      setPreviewUrl(images.length > 0 ? images[0].url : "");
      setPreviewBase64(
        images.length > 0 ? (images[0].images_base64?.full ?? "") : "",
      );
    }
  }, [versions]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!model) return null;

  const selectedVersion = versions.find((v) => v.id === selectedVersionId) ?? null;
  const selectedFile = (selectedVersion?.files ?? []).find(
    (f) => f.id === selectedFileId,
  ) ?? null;

  const stats = model.stats ?? {};
  const desc = model.description ? stripHtml(model.description) : "";

  /** Pick the largest available base64 size for a model image. */
  const bestBase64 = (img: VersionImage | undefined): string => {
    if (!img?.images_base64) return "";
    return img.images_base64.full
      || img.images_base64.medium
      || img.images_base64.small
      || "";
  };

  const handleVersionChange = (vid: number) => {
    setSelectedVersionId(vid);
    const v = versions.find((ver) => ver.id === vid);
    const files = v?.files ?? [];
    setSelectedFileId(files.length > 0 ? files[0].id : null);
    const images = v?.images ?? [];
    const firstImg = images[0];
    setPreviewUrl(firstImg?.url ?? "");
    setPreviewBase64(bestBase64(firstImg));
  };

  /** Pick the largest available size when a thumbnail is clicked. */
  const handleThumbnailClick = (img: VersionImage) => {
    setPreviewUrl(img.url);
    setPreviewBase64(bestBase64(img));
  };

  const handleDownload = async (key?: string) => {
    if (!selectedFile?.downloadUrl) return;
    try {
      const result = await startCivitaiFileDownload({
        url: selectedFile.downloadUrl,
        output_path: `/tmp/airunner/downloads/${selectedFile.name}`,
        api_key: key ?? "",
        base_model: currentBaseModel,
        model_type: currentModelType,
      });
      if (result.job_id) {
        addDownload({
          jobId: result.job_id,
          label: selectedFile.name,
          modelName: model?.name,
          baseModel: currentBaseModel,
          modelType: currentModelType,
          startedAt: new Date().toISOString(),
          downloadUrl: selectedFile.downloadUrl,
        });
      }
    } catch { /* */ }
  };

  const handleDownloadClick = () => {
    if (!selectedFile?.downloadUrl) return;
    setPendingDownloadUrl(selectedFile.downloadUrl);
    setPendingFileName(selectedFile.name ?? "");
    // Check if an API key is already stored; if not, show prompt
    const stored = localStorage.getItem("airunner_civitai_api_key");
    if (stored) {
      handleDownload(stored);
    } else {
      setShowApiKeyPrompt(true);
    }
  };

  const handleApiKeySubmit = () => {
    const trimmed = apiKey.trim();
    if (!trimmed) return;
    localStorage.setItem("airunner_civitai_api_key", trimmed);
    setShowApiKeyPrompt(false);
    handleDownload(trimmed);
  };

  if (loading) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.8)",
          zIndex: 1100,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        onClick={onClose}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div className="spinner-border text-light" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.8)",
        zIndex: 1100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: "relative",
          display: "flex",
          gap: 16,
          padding: 12,
          paddingTop: 44,
          maxHeight: "85vh",
          maxWidth: "90vw",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: 4,
          overflow: "hidden",
          background: "var(--theme-bg)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: 8,
            right: 8,
            background: "rgba(0,0,0,0.5)",
            border: "1px solid rgba(255,255,255,0.3)",
            color: "#fff",
            fontSize: 18,
            cursor: "pointer",
            lineHeight: 1,
            width: 30,
            height: 30,
            borderRadius: 4,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10,
          }}
          title="Close (Esc)"
        >
          ✕
        </button>

        {/* Preview image */}
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minWidth: 200,
            maxWidth: 500,
          }}
        >
          {previewUrl || previewBase64 ? (
            <CivitaiImage
              url={previewUrl}
              alt=""
              base64={previewBase64}
              width={400}
              style={{
                maxWidth: "100%",
                maxHeight: "75vh",
                objectFit: "contain",
                borderRadius: 4,
              }}
            />
          ) : (
            <div style={{ color: "#888", fontSize: 12 }}>No preview</div>
          )}
        </div>

        {/* Detail panel */}
        <div
          style={{
            width: 320,
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            color: "#ccc",
            fontSize: 12,
            gap: 8,
            overflow: "hidden",
          }}
        >
          {/* Model name + creator */}
          <div style={{ flexShrink: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 14, color: "#fff", marginBottom: 2 }}>
              {model.name}
            </div>
            <div style={{ color: "#aaa", fontSize: 11 }}>
              {model.creator ?? "Unknown"}
              {model.type ? ` · ${model.type}` : ""}
            </div>
            <div style={{ display: "flex", gap: 8, fontSize: 10, color: "#888", marginTop: 4 }}>
              <span>⬇ {stats.downloadCount ?? 0}</span>
              <span>★ {stats.favoriteCount ?? 0}</span>
              <span>💬 {stats.commentCount ?? 0}</span>
            </div>
          </div>

          {/* Scrollable content area */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
            {/* Description */}
            {desc && (
              <div
                style={{
                  fontSize: 10,
                  color: "#999",
                  lineHeight: 1.4,
                  marginBottom: 8,
                }}
              >
                {desc}
              </div>
            )}
            {/* Sample images */}
            {(selectedVersion?.images ?? []).length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ color: "#aaa", fontSize: 10, marginBottom: 4 }}>Sample Images</div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {(selectedVersion?.images ?? [])
                    .filter((img) => img.nsfw !== "X")
                    .slice(0, 8)
                    .map((img) => (
                      <div
                        key={img.url}
                        onClick={() => handleThumbnailClick(img)}
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: 4,
                          overflow: "hidden",
                          cursor: "pointer",
                          flexShrink: 0,
                          border: previewUrl === img.url ? "2px solid var(--bs-primary)" : "2px solid transparent",
                        }}
                      >
                        <CivitaiImage
                          url={img.url}
                          alt=""
                          base64={img.images_base64?.small}
                          width={48}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Version selector */}
            {versions.length > 0 && (
              <div style={{ marginBottom: 6 }}>
                <div style={{ color: "#aaa", fontSize: 10, marginBottom: 2 }}>Version</div>
                <select
                  value={selectedVersionId ?? ""}
                  onChange={(e) => handleVersionChange(Number(e.target.value))}
                  style={{
                    width: "100%",
                    background: "rgba(255,255,255,0.1)",
                    border: "1px solid rgba(255,255,255,0.2)",
                    borderRadius: 4,
                    color: "#fff",
                    fontSize: 11,
                    padding: "4px 6px",
                  }}
                >
                  {versions.map((v) => (
                    <option key={v.id} value={v.id} style={{ background: "#333" }}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* File selector */}
            {(selectedVersion?.files ?? []).length > 0 && (
              <div style={{ marginBottom: 6 }}>
                <div style={{ color: "#aaa", fontSize: 10, marginBottom: 2 }}>File</div>
                <select
                  value={selectedFileId ?? ""}
                  onChange={(e) => setSelectedFileId(Number(e.target.value))}
                  style={{
                    width: "100%",
                    background: "rgba(255,255,255,0.1)",
                    border: "1px solid rgba(255,255,255,0.2)",
                    borderRadius: 4,
                    color: "#fff",
                    fontSize: 11,
                    padding: "4px 6px",
                  }}
                >
                  {(selectedVersion?.files ?? []).map((f) => (
                    <option key={f.id} value={f.id} style={{ background: "#333" }}>
                      {f.name}
                      {f.sizeKB ? ` (${(f.sizeKB / 1024 / 1024).toFixed(1)} GB)` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
            <DownloadButton
              selectedFile={selectedFile}
              downloads={downloads}
              onDownloadClick={handleDownloadClick}
              onCancel={async (jobId: string) => {
                try { await cancelDownloadJob(jobId); } catch { /* */ }
                removeDownload(jobId);
              }}
            />
            <button
              onClick={() => window.open(`https://civitai.com/models/${model.id}`, "_blank")}
              style={{
                flexShrink: 0,
                padding: "6px 10px",
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: 4,
                color: "#aaa",
                cursor: "pointer",
                fontSize: 11,
              }}
            >
              ↗ CivitAI
            </button>
          </div>

          {/* Download progress */}
          {downloads.length > 0 && (
            <div style={{ flexShrink: 0 }}>
              {downloads.map((d) => (
                <div key={d.jobId} style={{ marginTop: 4 }}>
                  <DownloadProgress jobId={d.jobId} label={d.label} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* API Key prompt overlay */}
      {showApiKeyPrompt && (
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
          onClick={() => setShowApiKeyPrompt(false)}
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
              onKeyDown={(e) => { if (e.key === "Enter") handleApiKeySubmit(); }}
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
                onClick={handleApiKeySubmit}
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
                onClick={() => setShowApiKeyPrompt(false)}
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
      )}
    </div>
  );
}

/** Renders Download, Cancel, or Downloaded depending on file status. */
function DownloadButton({
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

  // Check: server-reported file existence, active downloads, and history
  if (selectedFile?.downloaded) {
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

  const alreadyDownloaded = downloadUrl ? isDownloaded(downloadUrl) : false;
  if (alreadyDownloaded) {
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
    // Save to completed history so it persists after Clear All
    setTimeout(() => checkDone(), 0);
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
