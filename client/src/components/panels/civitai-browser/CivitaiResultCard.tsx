import CivitaiImage from "./CivitaiImage";

interface ResultItem {
  id: number;
  name: string;
  type?: string;
  baseModel?: string;
  creator?: string;
  thumbnail?: string;
  /** Inline base64 thumbnails from the server, keyed by size. */
  thumbnails?: Record<string, string>;
}

interface CivitaiResultCardProps {
  item: ResultItem;
  selected: boolean;
  onSelect: (id: number) => void;
}

export default function CivitaiResultCard({
  item,
  selected,
  onSelect,
}: CivitaiResultCardProps) {
  const thumbBase64 = item.thumbnails?.small;
  const thumbUrl = item.thumbnail || "";
  return (
    <div
      data-model-id={item.id}
      onClick={() => onSelect(item.id)}
      style={{
        display: "flex",
        gap: 8,
        padding: "6px 4px",
        cursor: "pointer",
        background: selected
          ? "rgba(var(--theme-primary-rgb), 0.15)"
          : "transparent",
        borderRadius: 4,
        borderLeft: selected ? "2px solid var(--bs-primary)" : "2px solid transparent",
      }}
    >
      <div style={{ flexShrink: 0, width: 40, height: 40 }}>
        {thumbBase64 || thumbUrl ? (
          <CivitaiImage
            url={thumbUrl}
            alt={item.name}
            width={40}
            base64={thumbBase64}
            style={{
              width: 40,
              height: 40,
              borderRadius: 4,
              objectFit: "cover",
            }}
          />
        ) : (
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 4,
              background: "var(--theme-bg-secondary)",
            }}
          />
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0, fontSize: 11, lineHeight: 1.3 }}>
        <div className="text-truncate" style={{ fontWeight: 600 }}>
          {item.name}
        </div>
        <div className="text-muted text-truncate">
          {item.creator ?? "Unknown"}
        </div>
        <div className="text-muted text-truncate" style={{ fontSize: 10 }}>
          {item.type ?? ""}
          {item.baseModel ? ` · ${item.baseModel}` : ""}
        </div>
      </div>
    </div>
  );
}
