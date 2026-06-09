import LucideIcon from "../../../components/shared/LucideIcon";

const railBtnStyle: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  color: "rgba(255,255,255,0.4)", padding: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  borderRadius: 4, width: 28, height: 28, flexShrink: 0,
};

export type AssetTab = "layers" | "images";

const TABS: { id: AssetTab; icon: string; label: string }[] = [
  { id: "layers", icon: "layers", label: "Layers" },
  { id: "images", icon: "images", label: "Images" },
];

interface Props {
  activeTab: AssetTab;
  onExpand: (tab?: AssetTab) => void;
}

export default function CollapsedRail({ activeTab, onExpand }: Props) {
  return (
    <div style={{
      width: 32, flexShrink: 0, display: "flex", flexDirection: "column",
      alignItems: "center", background: "#181824",
      borderLeft: "1px solid rgba(255,255,255,0.07)",
      padding: "4px 0", gap: 2, overflow: "hidden",
    }}>
      <button style={railBtnStyle} title="Expand panel" onClick={() => onExpand()}>
        <LucideIcon name="chevron-left" size={14} />
      </button>
      <div style={{ width: "60%", height: 1, background: "rgba(255,255,255,0.07)", margin: "2px 0" }} />
      {TABS.map((t) => (
        <button
          key={t.id}
          style={{ ...railBtnStyle, color: activeTab === t.id ? "var(--bs-primary)" : "rgba(255,255,255,0.4)" }}
          title={t.label}
          onClick={() => onExpand(t.id)}
        >
          <LucideIcon name={t.icon} size={14} />
        </button>
      ))}
    </div>
  );
}
