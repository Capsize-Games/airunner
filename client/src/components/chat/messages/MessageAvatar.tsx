import LucideIcon from "../../shared/LucideIcon";

export default function MessageAvatar({
  isUser,
  label,
}: {
  isUser: boolean;
  label: string;
}) {
  return (
    <div className="d-flex align-items-center gap-2 mb-1">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: 28,
          height: 28,
          borderRadius: "50%",
          background: "rgba(255,255,255,0.08)",
          flexShrink: 0,
        }}
      >
        <LucideIcon name={isUser ? "user" : "bot-message-square"} size={16} />
      </div>
      <small className="fw-bold text-theme-secondary">
        {label}
      </small>
    </div>
  );
}
