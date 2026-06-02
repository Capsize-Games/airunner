const imgFilter = "var(--theme-icon-filter)";

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
              }}
            >
              <img
                src="/icons/lucide/dark/circle-check.svg"
                alt="Yes"
                style={{
                  width: 16,
                  height: 16,
                  filter: imgFilter,
                }}
              />
            </button>
            <button
              title="No"
              onClick={onCancelDeleteAll}
              style={{
                background: "none",
                border: "none",
                padding: 2,
                cursor: "pointer",
              }}
            >
              <img
                src="/icons/lucide/dark/circle-x.svg"
                alt="No"
                style={{
                  width: 16,
                  height: 16,
                  filter: imgFilter,
                }}
              />
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
