import LucideIcon from "../../shared/LucideIcon";

export default function ImageBrowserFooter({
  total,
  serverImagesCount,
  confirmDeleteAll,
  onDeleteAll,
  onConfirmDeleteAll,
  onCancelDeleteAll,
}: {
  total: number;
  serverImagesCount: number;
  confirmDeleteAll: boolean;
  onDeleteAll: () => void;
  onConfirmDeleteAll: () => void;
  onCancelDeleteAll: () => void;
}) {
  if (total === 0) return null;

  return (
    <div className="d-flex justify-content-between align-items-center mt-1">
      <div>
        {confirmDeleteAll ? (
          <div className="d-flex gap-2 align-items-center">
            <span className="small text-muted">
              Delete all {total} images?
            </span>
            <button
              title="Yes"
              onClick={onDeleteAll}
              style={{
                background: "none",
                border: "none",
                padding: 2,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
              }}
            >
              <LucideIcon name="circle-check" size={16} />
            </button>
            <button
              title="No"
              onClick={onCancelDeleteAll}
              style={{
                background: "none",
                border: "none",
                padding: 2,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
              }}
            >
              <LucideIcon name="circle-x" size={16} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={onConfirmDeleteAll}
            title="Delete all images for this date"
            style={{
              background: "none",
              border: "none",
              color: "var(--bs-danger)",
              fontSize: 12,
              cursor: "pointer",
              padding: 0,
              textDecoration: "underline",
              textUnderlineOffset: 2,
            }}
          >
            Delete All
          </button>
        )}
      </div>
      <div className="text-muted small text-end">
        {serverImagesCount} / {total}
      </div>
    </div>
  );
}
