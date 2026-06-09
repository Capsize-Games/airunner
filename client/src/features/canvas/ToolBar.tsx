import { FilePlus, Settings } from "lucide-react";

interface ToolBarProps {
  onOpenSettings: () => void;
  onNewDocument: () => void;
}

export default function ToolBar({ onOpenSettings, onNewDocument }: ToolBarProps) {
  const btn: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 5,
    padding: "3px 10px",
    background: "transparent",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 5,
    color: "rgba(255,255,255,0.55)",
    fontSize: 11,
    cursor: "pointer",
    flexShrink: 0,
    transition: "border-color 0.12s, color 0.12s",
  };

  const onEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.currentTarget.style.borderColor = "rgba(255,255,255,0.28)";
    e.currentTarget.style.color = "rgba(255,255,255,0.9)";
  };
  const onLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
    e.currentTarget.style.color = "rgba(255,255,255,0.55)";
  };

  return (
    <div
      className="d-flex align-items-center justify-content-between flex-shrink-0 user-select-none position-relative border-b-subtle"
      style={{ padding: "4px 8px", background: "#161620", zIndex: 100 }}
    >
      <button style={btn} onClick={onNewDocument} onMouseEnter={onEnter} onMouseLeave={onLeave}>
        <FilePlus size={13} strokeWidth={1.75} />
        New Document
      </button>

      <button style={btn} onClick={onOpenSettings} onMouseEnter={onEnter} onMouseLeave={onLeave}>
        <Settings size={13} strokeWidth={1.75} />
        Canvas Settings
      </button>
    </div>
  );
}
