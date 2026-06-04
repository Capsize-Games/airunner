import { useState } from "react";
import { BASE_URL } from "../../../types/api";
import type { ImageInfo } from "../../../api/client";
import { deleteImage, renameImage } from "../../../api/client";
import { formatFileSize, formatTimestamp } from "./LocalImageHelpers";
import LucideIcon from "../../../components/shared/LucideIcon";

export default function ServerImageRow({
  img,
  idx,
  selectedDate,
  onPreview,
  onDeleted,
}: {
  img: ImageInfo;
  idx: number;
  selectedDate: string | null;
  onPreview: (idx: number) => void;
  onDeleted: (id: string) => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [moveFeedback, setMoveFeedback] = useState<string | null>(null);

  const handleStartRename = () => {
    setEditingId(img.id);
    setEditValue(img.id);
  };

  const handleCommitRename = async () => {
    const newName = editValue.trim();
    if (!newName || newName === img.id || !selectedDate) {
      setEditingId(null);
      return;
    }
    setEditingId(null);
    try {
      await renameImage(selectedDate, img.id, newName);
    } catch {
      // revert — keep old id
    }
  };

  const handleCancelRename = () => {
    setEditingId(null);
  };

  const handleDelete = async () => {
    if (!selectedDate) return;
    try {
      await deleteImage(selectedDate, img.id);
      onDeleted(img.id);
      setConfirmDeleteId(null);
    } catch {
      // delete failed
    }
  };

  const handleMoveToCanvas = () => {
    window.dispatchEvent(
      new CustomEvent("canvas-place-image", {
        detail: { imageUrl: `${BASE_URL}${img.image_url}` },
      }),
    );
    setMoveFeedback(img.id);
    setTimeout(
      () => setMoveFeedback((prev) => (prev === img.id ? null : prev)),
      1500,
    );
  };

  const isEditing = editingId === img.id;

  return (
    <div
      key={img.id}
      className="d-flex border rounded p-1 mb-1"
      style={{
        backgroundColor: "rgba(255,255,255,0.02)",
        minHeight: 98,
      }}
    >
      {/* Thumbnail */}
      <div
        className="border rounded overflow-hidden flex-shrink-0 align-self-start"
        style={{ width: 96, height: 96, cursor: "pointer" }}
        title={`Click to preview: ${img.id}`}
        onClick={() => onPreview(idx)}
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData(
            "text/image-url",
            `${BASE_URL}${img.image_url}`,
          );
          e.dataTransfer.effectAllowed = "copy";
        }}
      >
        <img
          src={`${BASE_URL}${img.thumbnail_url}`}
          alt={img.id}
          className="w-100 h-100"
          style={{ objectFit: "cover" }}
          loading="lazy"
        />
      </div>

      {/* Info */}
      <div
        className="ms-2 flex-grow-1 overflow-hidden d-flex flex-column"
        style={{ minWidth: 0 }}
      >
        <div className="d-flex justify-content-between align-items-start">
          {isEditing ? (
            <input
              type="text"
              className="form-control form-control-sm"
              style={{ fontSize: 12, width: "100%", minWidth: 0 }}
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCommitRename();
                else if (e.key === "Escape") handleCancelRename();
              }}
              onBlur={handleCommitRename}
              autoFocus
            />
          ) : (
            <strong
              className="small"
              style={{ wordBreak: "break-all", cursor: "pointer" }}
              title="Click to rename"
              onClick={handleStartRename}
            >
              {img.id}
            </strong>
          )}
          <span className="small text-muted flex-shrink-0 ms-2">
            {formatFileSize(img.file_size)}
          </span>
        </div>
        <div className="small text-muted" style={{ fontSize: 11 }}>
          {formatTimestamp(img.file_timestamp)}
        </div>

        <div style={{ flex: 1 }} />

        <div
          className="d-flex gap-2 mt-1"
          style={{
            borderTop: "1px solid var(--theme-border)",
            paddingTop: 4,
            marginTop: 4,
            flexWrap: "wrap",
          }}
        >
          <button
            type="button"
            title={
              moveFeedback === img.id
                ? "Sent to canvas"
                : "Move to canvas"
            }
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 4,
              borderRadius: 4,
              opacity: 0.7,
              transition: "opacity 0.15s, background 0.15s",
              lineHeight: 1,
            }}
            onClick={handleMoveToCanvas}
            onMouseEnter={(e) => {
              e.currentTarget.style.background =
                "rgba(0,132,185,0.15)";
              e.currentTarget.style.opacity = "1";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "none";
              e.currentTarget.style.opacity = "0.7";
            }}
          >
            <LucideIcon name="panel-right-open" size={16} />
          </button>
          <button
            type="button"
            title="View details"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 4,
              borderRadius: 4,
              opacity: 0.7,
              transition: "opacity 0.15s, background 0.15s",
              lineHeight: 1,
            }}
            onClick={() => onPreview(idx)}
            onMouseEnter={(e) => {
              e.currentTarget.style.background =
                "rgba(0,132,185,0.15)";
              e.currentTarget.style.opacity = "1";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "none";
              e.currentTarget.style.opacity = "0.7";
            }}
          >
            <LucideIcon name="info" size={16} />
          </button>
          <button
            type="button"
            title="Delete image"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 4,
              borderRadius: 4,
              opacity: 0.7,
              transition: "opacity 0.15s, background 0.15s",
              lineHeight: 1,
            }}
            onClick={() =>
              setConfirmDeleteId(
                confirmDeleteId === img.id ? null : img.id,
              )
            }
            onMouseEnter={(e) => {
              e.currentTarget.style.background =
                "rgba(0,132,185,0.15)";
              e.currentTarget.style.opacity = "1";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "none";
              e.currentTarget.style.opacity = "0.7";
            }}
          >
            <LucideIcon name="trash" size={16} />
          </button>

          {confirmDeleteId === img.id && (
            <div className="d-flex gap-2 align-items-center">
              <span className="small text-muted">
                Delete this image?
              </span>
              <button
                title="Yes"
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 4,
                  borderRadius: 4,
                  opacity: 0.7,
                  transition: "opacity 0.15s, background 0.15s",
                  lineHeight: 1,
                }}
                onClick={handleDelete}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background =
                    "rgba(0,132,185,0.15)";
                  e.currentTarget.style.opacity = "1";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "none";
                  e.currentTarget.style.opacity = "0.7";
                }}
              >
                <LucideIcon name="circle-check" size={16} />
              </button>
              <button
                title="No"
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 4,
                  borderRadius: 4,
                  opacity: 0.7,
                  transition: "opacity 0.15s, background 0.15s",
                  lineHeight: 1,
                }}
                onClick={() => setConfirmDeleteId(null)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background =
                    "rgba(0,132,185,0.15)";
                  e.currentTarget.style.opacity = "1";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "none";
                  e.currentTarget.style.opacity = "0.7";
                }}
              >
                <LucideIcon name="circle-x" size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
