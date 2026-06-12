import { useState, useCallback } from "react";
import type { ImageInfo } from "../../../api/client";
import { deleteImage, renameImage } from "../../../api/client";
import { formatFileSize, formatTimestamp } from "./LocalImageHelpers";
import LucideIcon from "../../../components/shared/LucideIcon";
import { useAuthenticatedBlobUrl } from "../../../hooks/useAuthenticatedBlobUrl";
import { BASE_URL } from "../../../types/api";
import ImageContextMenu, {
  fetchImageBlob,
  saveBlobToDisk,
  type ContextMenuAction,
} from "./ImageContextMenu";

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
  const [ctxMenuPos, setCtxMenuPos] = useState<{
    x: number;
    y: number;
  } | null>(null);

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setCtxMenuPos({ x: e.clientX, y: e.clientY });
    },
    [],
  );

  const thumbnailBlobUrl = useAuthenticatedBlobUrl(img.thumbnail_url);
  const imageBlobUrl = useAuthenticatedBlobUrl(img.image_url);

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
        detail: {
          imageUrl:
            imageBlobUrl ?? `${BASE_URL}${img.image_url}`,
        },
      }),
    );
    setMoveFeedback(img.id);
    setTimeout(
      () =>
        setMoveFeedback((prev) =>
          prev === img.id ? null : prev,
        ),
      1500,
    );
  };

  const handleExport = async () => {
    try {
      const blob = await fetchImageBlob(img.image_url);
      await saveBlobToDisk(blob, `${img.id}.png`);
    } catch {
      // export failed silently
    }
  };

  const isEditing = editingId === img.id;

  const actions: (ContextMenuAction | "divider")[] = [
    {
      label: "Move to canvas",
      icon: "panel-right-open",
      onClick: handleMoveToCanvas,
    },
    {
      label: "View image details",
      icon: "info",
      onClick: () => onPreview(idx),
    },
    "divider",
    {
      label: "Export image",
      icon: "download",
      onClick: handleExport,
    },
    "divider",
    {
      label: "Delete",
      icon: "trash",
      onClick: handleDelete,
      danger: true,
    },
  ];

  return (
    <>
      <div
        key={img.id}
        className="d-flex border rounded p-1 mb-1"
        style={{
          backgroundColor: "rgba(255,255,255,0.02)",
          minHeight: 98,
        }}
        onContextMenu={handleContextMenu}
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
              imageBlobUrl ?? `${BASE_URL}${img.image_url}`,
            );
            e.dataTransfer.effectAllowed = "copy";
          }}
        >
          <img
            src={thumbnailBlobUrl ?? undefined}
            alt={img.id}
            className="w-100 h-100"
            style={{ objectFit: "cover" }}
            loading="lazy"
          />
        </div>

        {/* Info */}
        <div className="ms-2 flex-grow-1 overflow-hidden d-flex flex-column min-w-0">
          <div className="d-flex justify-content-between align-items-start">
            {isEditing ? (
              <input
                type="text"
                className="form-control form-control-sm"
                style={{
                  fontSize: 12,
                  width: "100%",
                  minWidth: 0,
                }}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCommitRename();
                  else if (e.key === "Escape")
                    handleCancelRename();
                }}
                onBlur={handleCommitRename}
                autoFocus
              />
            ) : (
              <strong
                className="small"
                style={{
                  wordBreak: "break-all",
                  cursor: "pointer",
                }}
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

          <div className="flex-grow-1" />

          <div
            className="d-flex gap-2 mt-1 border-t-theme flex-wrap"
            style={{ paddingTop: 4, marginTop: 4 }}
          >
            <button
              type="button"
              className="icon-btn"
              title={
                moveFeedback === img.id
                  ? "Sent to canvas"
                  : "Move to canvas"
              }
              onClick={handleMoveToCanvas}
            >
              <LucideIcon name="panel-right-open" size={16} />
            </button>
            <button
              type="button"
              className="icon-btn"
              title="View details"
              onClick={() => onPreview(idx)}
            >
              <LucideIcon name="info" size={16} />
            </button>
            <button
              type="button"
              className="icon-btn"
              title="Delete image"
              onClick={() =>
                setConfirmDeleteId(
                  confirmDeleteId === img.id ? null : img.id,
                )
              }
            >
              <LucideIcon name="trash" size={16} />
            </button>

            {confirmDeleteId === img.id && (
              <div className="d-flex gap-2 align-items-center">
                <span className="small text-muted">
                  Delete this image?
                </span>
                <button
                  className="icon-btn"
                  title="Yes"
                  onClick={handleDelete}
                >
                  <LucideIcon name="circle-check" size={16} />
                </button>
                <button
                  className="icon-btn"
                  title="No"
                  onClick={() => setConfirmDeleteId(null)}
                >
                  <LucideIcon name="circle-x" size={16} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {ctxMenuPos && (
        <ImageContextMenu
          x={ctxMenuPos.x}
          y={ctxMenuPos.y}
          actions={actions}
          onClose={() => setCtxMenuPos(null)}
        />
      )}
    </>
  );
}
