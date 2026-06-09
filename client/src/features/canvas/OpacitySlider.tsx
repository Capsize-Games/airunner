import Form from "react-bootstrap/Form";

interface OpacitySliderProps {
  value: number;
  onChange: (val: number) => void;
}

export default function OpacitySlider({ value, onChange }: OpacitySliderProps) {
  return (
    <div
      className="flex-shrink-0 border-b-subtle"
      style={{ padding: "4px 8px 6px" }}
    >
      <div className="d-flex align-items-center" style={{ gap: 0 }}>
        <span style={{
          fontSize: 9,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "rgba(255,255,255,0.35)",
          padding: "2px 6px",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRight: "none",
          borderRadius: "4px 0 0 4px",
          background: "rgba(0,0,0,0.15)",
          flexShrink: 0,
        }}>
          Opacity
        </span>
        <div style={{
          flex: 1,
          border: "1px solid rgba(255,255,255,0.12)",
          borderLeft: "none",
          borderRight: "none",
          display: "flex",
          alignItems: "center",
          padding: "0 4px",
        }}>
          <Form.Range
            min={0} max={1} step={0.01}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            style={{ marginBottom: 0, flexGrow: 1 }}
          />
        </div>
        <span style={{
          fontSize: 10,
          fontFamily: "monospace",
          color: "rgba(255,255,255,0.45)",
          padding: "2px 6px",
          border: "1px solid rgba(255,255,255,0.12)",
          borderLeft: "none",
          borderRadius: "0 4px 4px 0",
          background: "rgba(0,0,0,0.15)",
          flexShrink: 0,
          minWidth: 36,
          textAlign: "center",
        }}>
          {Math.round(value * 100)}%
        </span>
      </div>
    </div>
  );
}
