import LucideIcon from "../../shared/LucideIcon";

export default function EmptyPlaceholder() {
  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          padding: "36px 10px",
          maxWidth: "150px",
          border: "1px solid rgba(255,255,255,0.10)",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: "rgba(255,255,255,0.06)",
          }}
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
