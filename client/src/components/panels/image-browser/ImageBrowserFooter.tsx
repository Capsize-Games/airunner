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
            <button className="icon-btn" title="Yes" onClick={onDeleteAll}>
              <LucideIcon name="circle-check" size={16} />
            </button>
            <button className="icon-btn" title="No" onClick={onCancelDeleteAll}>
              <LucideIcon name="circle-x" size={16} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="btn-text-danger"
            onClick={onConfirmDeleteAll}
            title="Delete all images for this date"
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
