import LucideIcon from "../../shared/LucideIcon";

export default function EmptyPlaceholder() {
  return (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: "100%" }}>
      <div
        className="d-flex flex-column align-items-center"
        style={{
          gap: 14,
          padding: "36px 10px",
          maxWidth: "150px",
          border: "1px solid rgba(255,255,255,0.10)",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
        }}
      >
        <div
          className="d-flex align-items-center justify-content-center"
          style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(255,255,255,0.06)" }}
        >
          <LucideIcon name="bot-message-square" size={24} />
        </div>
        <p
          style={{
            margin: 0,
            fontSize: "0.85rem",
            color: "rgba(255,255,255,0.35)",
            textAlign: "center",
            lineHeight: 1.5,
          }}
        >
          Start a conversation by typing a message below.
        </p>
      </div>
    </div>
  );
}
