interface Props {
  currentIndex: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
}

const btnBase: React.CSSProperties = {
  flex: 1, padding: "6px 12px",
  border: "1px solid rgba(255,255,255,0.2)",
  borderRadius: 4, fontSize: 13,
};

export default function ModalNavigation({ currentIndex, total, onPrev, onNext }: Props) {
  const atStart = currentIndex <= 0;
  const atEnd = currentIndex >= total - 1;

  return (
    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16, gap: 8, alignItems: "center", flexShrink: 0 }}>
      <button
        onClick={onPrev}
        disabled={atStart}
        style={{ ...btnBase, background: atStart ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.2)", color: atStart ? "#666" : "#fff", cursor: atStart ? "default" : "pointer" }}
      >
        ◀ Previous
      </button>
      <span style={{ color: "#aaa", fontSize: 12, whiteSpace: "nowrap" }}>
        {currentIndex + 1} / {total}
      </span>
      <button
        onClick={onNext}
        disabled={atEnd}
        style={{ ...btnBase, background: atEnd ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.2)", color: atEnd ? "#666" : "#fff", cursor: atEnd ? "default" : "pointer" }}
      >
        Next ▶
      </button>
    </div>
  );
}
