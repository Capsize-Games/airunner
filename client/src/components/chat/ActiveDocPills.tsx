interface ActiveDoc {
  id: number;
  name: string;
}

export default function ActiveDocPills({
  activeDocs,
  onRemoveDoc,
}: {
  activeDocs: ActiveDoc[];
  onRemoveDoc: (id: number) => void;
}) {
  if (activeDocs.length === 0) return null;

  return (
    <div className="d-flex flex-wrap gap-1">
      {activeDocs.map((doc) => (
        <span
          key={doc.id}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            background: "rgba(0,132,185,0.2)",
            border: "1px solid var(--bs-primary)",
            borderRadius: 12,
            padding: "2px 8px",
            fontSize: "0.7rem",
            color: "var(--theme-text)",
          }}
        >
          <span
            style={{
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              lineHeight: 1,
              color: "#ff5555",
              fontSize: "0.8rem",
            }}
            onClick={() => onRemoveDoc(doc.id)}
            title="Remove from RAG"
          >
            ✕
          </span>
          {doc.name}
        </span>
      ))}
    </div>
  );
}
