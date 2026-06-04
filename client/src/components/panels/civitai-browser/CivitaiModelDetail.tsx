import { useState, useMemo } from "react";
import CivitaiSampleImages from "./CivitaiSampleImages";
import CivitaiImage from "./CivitaiImage";

interface CivitaiVersion {
  id: number;
  name: string;
  baseModel?: string;
  files?: CivitaiFile[];
  images?: CivitaiImageInfo[];
  downloadUrl?: string;
}

interface CivitaiFile {
  id: number;
  name: string;
  sizeKB?: number;
  downloadUrl?: string;
}

interface CivitaiImageInfo {
  url: string;
  nsfw?: string;
  width?: number;
  height?: number;
}

interface CivitaiModelDetailProps {
  model: {
    id: number;
    name: string;
    description?: string;
    creator?: string;
    type?: string;
    stats?: {
      downloadCount?: number;
      favoriteCount?: number;
      commentCount?: number;
    };
    versions?: CivitaiVersion[];
  } | null;
  onDownload: (fileUrl: string, fileName: string) => void;
}

function stripHtml(html: string): string {
  // Remove HTML tags using a DOMParser which handles edge cases
  // like <<tag> better than a plain regex.
  if (typeof DOMParser !== "undefined") {
    const doc = new DOMParser().parseFromString(html, "text/html");
    return (doc.body.textContent ?? "").trim();
  }
  return html.replace(/<[^>]*>/g, "").trim();
}

export default function CivitaiModelDetail({
  model,
  onDownload,
}: CivitaiModelDetailProps) {
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(
    null,
  );
  const [selectedFileId, setSelectedFileId] = useState<number | null>(
    null,
  );

  const versions = model?.versions ?? [];

  // Auto-select first version when model changes
  useMemo(() => {
    if (versions.length > 0) {
      setSelectedVersionId(versions[0].id);
      const files = versions[0].files ?? [];
      if (files.length > 0) {
        setSelectedFileId(files[0].id);
      }
    }
  }, [versions]);

  const selectedVersion = versions.find(
    (v) => v.id === selectedVersionId,
  ) ?? null;
  const selectedFile = (selectedVersion?.files ?? []).find(
    (f) => f.id === selectedFileId,
  ) ?? null;

  if (!model) {
    return (
      <div
        className="text-muted"
        style={{
          fontSize: 12,
          padding: 16,
          textAlign: "center",
        }}
      >
        Select a model to view details
      </div>
    );
  }

  const stats = model.stats ?? {};
  const desc = model.description ? stripHtml(model.description) : "";

  const handleDownload = () => {
    if (!selectedFile?.downloadUrl) return;
    const fileName = selectedFile.name;
    onDownload(selectedFile.downloadUrl, fileName);
  };

  return (
    <div style={{ fontSize: 11, padding: "0 2px" }}>
      {/* Model name + creator */}
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 2 }}>
        {model.name}
      </div>
      <div className="text-muted mb-1">
        {model.creator ?? "Unknown"}
        {model.type ? ` · ${model.type}` : ""}
      </div>

      {/* Stats */}
      <div
        className="d-flex gap-2 mb-1"
        style={{ fontSize: 10, color: "#888" }}
      >
        <span>⬇ {stats.downloadCount ?? 0}</span>
        <span>★ {stats.favoriteCount ?? 0}</span>
        <span>💬 {stats.commentCount ?? 0}</span>
      </div>

      {/* Description (truncated) */}
      {desc && (
        <div
          className="mb-1 text-muted"
          style={{
            fontSize: 10,
            maxHeight: 60,
            overflow: "hidden",
            lineHeight: 1.4,
          }}
        >
          {desc.length > 200 ? desc.slice(0, 200) + "..." : desc}
        </div>
      )}

      {/* Version selector */}
      {versions.length > 0 && (
        <div className="mb-1">
          <small className="text-muted d-block mb-1">Version</small>
          <select
            className="form-select form-select-sm"
            value={selectedVersionId ?? ""}
            onChange={(e) => {
              const vid = Number(e.target.value);
              setSelectedVersionId(vid);
              const v = versions.find((ver) => ver.id === vid);
              const files = v?.files ?? [];
              setSelectedFileId(
                files.length > 0 ? files[0].id : null,
              );
            }}
            style={{ fontSize: 11 }}
          >
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* File selector */}
      {(selectedVersion?.files ?? []).length > 0 && (
        <div className="mb-1">
          <small className="text-muted d-block mb-1">File</small>
          <select
            className="form-select form-select-sm"
            value={selectedFileId ?? ""}
            onChange={(e) => setSelectedFileId(Number(e.target.value))}
            style={{ fontSize: 11 }}
          >
            {(selectedVersion?.files ?? []).map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
                {f.sizeKB
                  ? ` (${(f.sizeKB / 1024 / 1024).toFixed(1)} GB)`
                  : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Sample images */}
      <CivitaiSampleImages
        images={(selectedVersion?.images ?? []).filter(
          (img) => img.nsfw !== "X",
        )}
      />

      {/* Action buttons */}
      <div className="d-flex gap-1 mb-1">
        <button
          className="btn btn-sm btn-outline-primary flex-grow-1"
          onClick={handleDownload}
          disabled={!selectedFile?.downloadUrl}
          style={{ fontSize: 11 }}
        >
          Download
        </button>
        <button
          className="btn btn-sm btn-outline-secondary"
          onClick={() =>
            window.open(
              `https://civitai.com/models/${model.id}`,
              "_blank",
            )
          }
          style={{ fontSize: 11 }}
          title="Open on CivitAI"
        >
          ↗
        </button>
      </div>
    </div>
  );
}
