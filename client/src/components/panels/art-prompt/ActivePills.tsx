const iconFilter = "var(--theme-icon-filter)";

interface ActivePill {
  id: number;
  name: string;
}

export function EmbeddingPills({
  embeddings,
  onDeactivate,
}: {
  embeddings: ActivePill[];
  onDeactivate: (id: number) => void;
}) {
  if (embeddings.length === 0) return null;

  return (
    <div
      className="mb-1 p-2 rounded"
      style={{
        background: "rgba(0,132,185,0.05)",
        border: "1px solid rgba(0,132,185,0.25)",
      }}
    >
      <small
        style={{
          color: "#0084b8",
          display: "block",
          marginBottom: 4,
          fontSize: "0.65rem",
          fontWeight: 700,
        }}
      >
        Active Embeddings
      </small>
      <div className="d-flex flex-wrap gap-1">
        {embeddings.map((emb) => (
          <span
            key={emb.id}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              background: "rgba(0,132,185,0.2)",
              border: "1px solid #0084b8",
              borderRadius: 12,
              padding: "2px 8px",
              fontSize: "0.7rem",
              color: "var(--theme-text)",
            }}
          >
            <span
              style={{
                cursor: "pointer",
                color: "#ff5555",
                fontSize: "0.7rem",
                lineHeight: 1,
              }}
              onClick={() => onDeactivate(emb.id)}
              title="Deactivate embedding"
            >
              ✕
            </span>
            {emb.name}
          </span>
        ))}
      </div>
    </div>
  );
}

export function LoraPills({
  loras,
  onDeactivate,
}: {
  loras: ActivePill[];
  onDeactivate: (id: number) => void;
}) {
  if (loras.length === 0) return null;

  return (
    <div
      className="mb-1 p-2 rounded"
      style={{
        background: "rgba(185,0,132,0.05)",
        border: "1px solid rgba(184,0,132,0.25)",
      }}
    >
      <small
        style={{
          color: "#b80084",
          display: "block",
          marginBottom: 4,
          fontSize: "0.65rem",
          fontWeight: 700,
        }}
      >
        Active LoRA
      </small>
      <div className="d-flex flex-wrap gap-1">
        {loras.map((lora) => (
          <span
            key={lora.id}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              background: "rgba(185,0,132,0.2)",
              border: "1px solid #b80084",
              borderRadius: 12,
              padding: "2px 8px",
              fontSize: "0.7rem",
              color: "var(--theme-text)",
            }}
          >
            <span
              style={{
                cursor: "pointer",
                color: "#ff5555",
                fontSize: "0.7rem",
                lineHeight: 1,
              }}
              onClick={() => onDeactivate(lora.id)}
              title="Deactivate LoRA"
            >
              ✕
            </span>
            {lora.name}
          </span>
        ))}
      </div>
    </div>
  );
}
