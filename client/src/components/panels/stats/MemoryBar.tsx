const progressOuter: React.CSSProperties = {
  width: "100%", height: 8, background: "#333",
  borderRadius: 4, marginTop: 4, overflow: "hidden",
};

interface Props {
  label: string;
  usedGb: number;
  totalGb: number;
  highColor: string;
  lowColor: string;
}

export default function MemoryBar({ label, usedGb, totalGb, highColor, lowColor }: Props) {
  const pct = totalGb > 0 ? (usedGb / totalGb) * 100 : 0;
  return (
    <div className="mb-2">
      <small className="text-muted">{label}</small>
      <div style={progressOuter}>
        <div style={{
          height: "100%",
          borderRadius: 4,
          transition: "width 0.3s ease",
          width: `${Math.min(pct, 100)}%`,
          backgroundColor: pct > 90 ? highColor : lowColor,
        }} />
      </div>
      <small className="text-muted">
        {usedGb.toFixed(1)} / {totalGb.toFixed(1)} GB
      </small>
    </div>
  );
}
