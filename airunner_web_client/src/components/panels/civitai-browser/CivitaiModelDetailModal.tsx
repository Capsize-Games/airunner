import { useEffect, useCallback, useState, useRef } from "react";
import { BASE_URL } from "../../../types/api";
import CivitaiImage from "./CivitaiImage";
import DownloadProgress from "../../downloads/DownloadProgress";
import { startCivitaiFileDownload } from "../../../api/downloads";
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
}

interface ModelDetailData {
  id: number;
  name: string;
  description?: string;
  creator?: string;
  type?: string;
  stats?: { downloadCount?: number; favoriteCount?: number; commentCount?: number };
  versions?: CivitaiVersion[];
}

interface CivitaiModelDetailModalProps {
  model: ModelDetailData | null;
  onClose: () => void;
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, "").trim();
}

interface DownloadJob {
  jobId: string;
  label: string;
}

export default function CivitaiModelDetailModal({
  model,
  onClose,
}: CivitaiModelDetailModalProps) {
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>("");
  const [previewBase64, setPreviewBase64] = useState<string>("");
  const [downloads, setDownloads] = useState<DownloadJob[]>([]);

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

  const handleVersionChange = (vid: number) => {
    setSelectedVersionId(vid);
    const v = versions.find((ver) => ver.id === vid);
    const files = v?.files ?? [];
    setSelectedFileId(files.length > 0 ? files[0].id : null);
    const images = v?.images ?? [];
    setPreviewUrl(images.length > 0 ? images[0].url : "");
    setPreviewBase64(
      images.length > 0 ? (images[0].images_base64?.full ?? "") : "",
    );
  };

  const handleDownload = async () => {
    if (!selectedFile?.downloadUrl) return;
    try {
      const result = await startCivitaiFileDownload({
        url: selectedFile.downloadUrl,
        output_path: `/tmp/airunner/downloads/${selectedFile.name}`,
      });
      if (result.job_id) {
        setDownloads((prev) => [...prev, { jobId: result.job_id, label: selectedFile.name }]);
      }
    } catch { /* */ }
  };

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

          {/* Description */}
          {desc && (
            <div
              style={{
                fontSize: 10,
                color: "#999",
                maxHeight: 60,
                overflow: "hidden",
                lineHeight: 1.4,
                flexShrink: 0,
              }}
            >
              {desc.length > 300 ? desc.slice(0, 300) + "..." : desc}
            </div>
          )}

          {/* Scrollable content area */}
          <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
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
                        onClick={() => {
                          setPreviewUrl(img.url);
                          setPreviewBase64(img.images_base64?.full ?? "");
                        }}
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
            <button
              onClick={handleDownload}
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
    </div>
  );
}
