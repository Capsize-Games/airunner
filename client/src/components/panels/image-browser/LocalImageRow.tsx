import type { LocalImageEntry } from "./LocalImageHelpers";
import { formatFileSize, truncate } from "./LocalImageHelpers";

export default function LocalImageRow({
  entry,
  onDelete,
}: {
  entry: LocalImageEntry;
  onDelete: (id: string) => void;
}) {
  return (
    <div
      key={`local-${entry.id}`}
      className="d-flex border rounded p-1 mb-1 align-items-start"
      style={{ backgroundColor: "rgba(255,255,255,0.02)" }}
    >
      <div
        className="border rounded overflow-hidden flex-shrink-0"
        style={{ width: 96, height: 96 }}
      >
        <img
          src={entry.dataUrl}
          alt={entry.id}
          className="w-100 h-100"
          style={{ objectFit: "cover" }}
          loading="lazy"
        />
      </div>

      <div className="ms-2 flex-grow-1 overflow-hidden">
        <div className="d-flex justify-content-between align-items-start">
          <strong className="small" style={{ wordBreak: "break-all" }}>
            {entry.id}
          </strong>
          <span className="small text-muted flex-shrink-0 ms-1">
            {formatFileSize(entry.fileSize)}
          </span>
        </div>

        <div className="small text-muted">
          Stored locally · {entry.timestamp}
          <button
            className="btn btn-link btn-sm p-0 ms-1 small text-danger"
            onClick={() => onDelete(entry.id)}
            title="Delete local image"
            style={{ verticalAlign: "baseline" }}
          >
            Delete
          </button>
        </div>

        {(entry.prompt || entry.seed || entry.steps) && (
          <div
            className="small text-muted mt-1"
            style={{ lineHeight: 1.4 }}
          >
            {entry.prompt && (
              <span className="me-2">
                <strong>prompt:</strong> {truncate(entry.prompt, 40)}{" "}
              </span>
            )}
            {entry.seed !== undefined && (
              <span className="me-2">
                <strong>seed:</strong> {entry.seed}{" "}
              </span>
            )}
            {entry.steps !== undefined && (
              <span className="me-2">
                <strong>steps:</strong> {entry.steps}{" "}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
