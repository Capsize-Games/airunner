import LucideIcon from "../../../components/shared/LucideIcon";

const railBtnStyle: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  color: "rgba(255,255,255,0.4)", padding: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  borderRadius: 4, width: 28, height: 28, flexShrink: 0,
  transition: "background 0.1s, color 0.1s",
};

export type AssetTab = "layers" | "images";

const TABS: { id: AssetTab; icon: string; label: string }[] = [
  { id: "layers", icon: "layers", label: "Layers" },
  { id: "images", icon: "images", label: "Images" },
];

function onRailBtnEnter(e: React.MouseEvent<HTMLButtonElement>) {
  const btn = e.currentTarget;
  const isActive = btn.style.color === "var(--bs-primary)";
  if (!isActive) {
    btn.style.background = "rgba(255,255,255,0.08)";
    btn.style.color = "rgba(255,255,255,0.85)";
  }
}

function onRailBtnLeave(e: React.MouseEvent<HTMLButtonElement>) {
  const btn = e.currentTarget;
  if (!btn.style.color.includes("--bs-primary")) {
    btn.style.background = "none";
    btn.style.color = "rgba(255,255,255,0.4)";
  }
}

interface Props {
  activeTab: AssetTab;
  onExpand: (tab?: AssetTab) => void;
}

export default function CollapsedRail({ activeTab, onExpand }: Props) {
  return (
    <div
      className="flex-shrink-0 d-flex flex-column align-items-center overflow-hidden"
      style={{ width: 32, background: "#181824", borderLeft: "1px solid rgba(255,255,255,0.07)", padding: "4px 0", gap: 2 }}
    >
      <button style={railBtnStyle} title="Expand panel" onClick={() => onExpand()}
        onMouseEnter={onRailBtnEnter} onMouseLeave={onRailBtnLeave}>
        <LucideIcon name="chevron-left" size={14} />
      </button>
      <div className="sep-h" />
      {TABS.map((t) => (
        <button
          key={t.id}
          style={{ ...railBtnStyle, color: activeTab === t.id ? "var(--bs-primary)" : "rgba(255,255,255,0.4)" }}
          title={t.label}
          onClick={() => onExpand(t.id)}
          onMouseEnter={onRailBtnEnter}
          onMouseLeave={onRailBtnLeave}
        >
          <LucideIcon name={t.icon} size={14} />
        </button>
      ))}
    </div>
  );
}
