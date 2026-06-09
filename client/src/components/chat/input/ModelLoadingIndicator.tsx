import LucideIcon from "../../shared/LucideIcon";

export default function ModelLoadingIndicator({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div
      className="p-2 rounded w-100 mt-2"
      style={{
        background: "rgba(255,193,7,0.10)",
        border: "1px solid rgba(255,193,7,0.20)",
      }}
    >
      <div className="d-flex align-items-center gap-2">
        <LucideIcon name="loader" size={16} />
        <small className="text-theme-secondary">
          Loading model…
        </small>
      </div>
    </div>
  );
}
