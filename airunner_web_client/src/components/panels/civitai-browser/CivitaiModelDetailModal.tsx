import { useEffect, useCallback, useState, useRef } from "react";
import { BASE_URL } from "../../../types/api";
import CivitaiImage from "./CivitaiImage";
import { startCivitaiFileDownload, cancelDownloadJob } from "../../../api/downloads";
import { useDownloads } from "../../downloads/useDownloadState";
import { DownloadButton, ApiKeyPrompt } from "./CivitaiModelDetailDownload";
import type { ModelDetailData, CivitaiVersion, CivitaiFile, VersionImage } from "./CivitaiModelDetailTypes";

interface CivitaiModelDetailModalProps {
  model: ModelDetailData | null;
  onClose: () => void;
  loading?: boolean;
  baseModel?: string;
  modelType?: string;
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, "").trim();
}

interface DownloadJobRef {
  jobId: string;
  label: string;
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

  if (loading) {
    return (
      <div
        style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)",
          zIndex: 1100, display: "flex", alignItems: "center", justifyContent: "center",
        }}
        onClick={onClose}
      >
        <div className="spinner-border text-light" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  if (!model) return null;

  const selectedVersion = versions.find((v) => v.id === selectedVersionId) ?? null;
  const selectedFile = (selectedVersion?.files ?? []).find(
    (f) => f.id === selectedFileId,
  ) ?? null;

  const stats = model.stats ?? {};
  const desc = model.description ? stripHtml(model.description) : "";

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
    setPendingFileName(selectedFile.name ?? "");
    const stored = localStorage.getItem("airunner_civitai_api_key");
    if (stored) {
      handleDownload(stored);
    } else {
      setShowApiKeyPrompt(true);
    }
  };

  const handleApiKeySubmit = (key: string) => {
    setShowApiKeyPrompt(false);
    handleDownload(key);
  };

  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)",
        zIndex: 1100, display: "flex", alignItems: "center", justifyContent: "center",
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: "relative", display: "flex", gap: 16, padding: 12, paddingTop: 44,
          maxHeight: "85vh", maxWidth: "90vw",
          border: "1px solid rgba(255,255,255,0.2)", borderRadius: 4,
          overflow: "hidden", background: "var(--theme-bg)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: 8, right: 8,
            background: "rgba(0,0,0,0.5)", border: "1px solid rgba(255,255,255,0.3)",
            color: "#fff", fontSize: 18, cursor: "pointer", lineHeight: 1,
            width: 30, height: 30, borderRadius: 4,
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10,
          }}
          title="Close (Esc)"
        >
          ✕
        </button>

        {/* Preview image */}
        <div
          style={{
            flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
            minWidth: 200, maxWidth: 500,
          }}
        >
          {previewUrl || previewBase64 ? (
            <CivitaiImage
              url={previewUrl}
              alt=""
              base64={previewBase64}
              width={400}
              style={{ maxWidth: "100%", maxHeight: "75vh", objectFit: "contain", borderRadius: 4 }}
            />
          ) : (
            <div style={{ color: "#888", fontSize: 12 }}>No preview</div>
          )}
        </div>

        {/* Detail panel */}
        <div
          style={{
            width: 320, display: "flex", flexDirection: "column",
            color: "#ccc", fontSize: 12, gap: 8, overflow: "hidden",
          }}
        >
          {/* Header */}
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

          {/* License badges */}
          {model && (
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap", flexShrink: 0 }}>
              {model.allowNoCredit === true && <span title="Use without credit" style={{ fontSize: 14, cursor: "help" }}>🙏</span>}
              {model.allowCommercialUse === "Commercial" && <span title="Commercial use allowed" style={{ fontSize: 14, cursor: "help" }}>💰</span>}
              {model.allowCommercialUse === "Non-Commercial" && <span title="Non-commercial only" style={{ fontSize: 14, cursor: "help" }}>🚫💰</span>}
              {model.allowDerivatives === "Allowed" && <span title="Derivatives allowed" style={{ fontSize: 14, cursor: "help" }}>🔀</span>}
              {model.allowDerivatives === "Not allowed" && <span title="No derivatives" style={{ fontSize: 14, cursor: "help" }}>🚫🔀</span>}
              {model.allowDifferentLicense === true && <span title="Can use different license" style={{ fontSize: 14, cursor: "help" }}>📜</span>}
            </div>
          )}

          {/* Scrollable content area */}
          <div className="scrollable-modal-content" style={{ flex: 1, overflowY: "auto", minHeight: 0, height: 0 }}>
            {/* Description */}
            {desc && (
              <div
                className="civitai-model-description"
                style={{ fontSize: 10, color: "#999", lineHeight: 1.4, marginBottom: 8 }}
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
                          width: 48, height: 48, borderRadius: 4, overflow: "hidden",
                          cursor: "pointer", flexShrink: 0,
                          border: previewUrl === img.url ? "2px solid var(--bs-primary)" : "2px solid transparent",
                        }}
                      >
                        <CivitaiImage
                          url={img.url} alt=""
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
                    width: "100%", background: "rgba(255,255,255,0.1)",
                    border: "1px solid rgba(255,255,255,0.2)", borderRadius: 4,
                    color: "#fff", fontSize: 11, padding: "4px 6px",
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
                    width: "100%", background: "rgba(255,255,255,0.1)",
                    border: "1px solid rgba(255,255,255,0.2)", borderRadius: 4,
                    color: "#fff", fontSize: 11, padding: "4px 6px",
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
                flexShrink: 0, padding: "6px 10px",
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.2)", borderRadius: 4,
                color: "#aaa", cursor: "pointer", fontSize: 11,
              }}
            >
              ↗ CivitAI
            </button>
          </div>
        </div>
      </div>

      {showApiKeyPrompt && (
        <ApiKeyPrompt
          onSubmit={handleApiKeySubmit}
          onCancel={() => setShowApiKeyPrompt(false)}
        />
      )}
    </div>
  );
}
