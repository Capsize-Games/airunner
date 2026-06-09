import Form from "react-bootstrap/Form";

interface OpacitySliderProps {
  value: number;
  onChange: (val: number) => void;
}

/**
 * Anchored opacity slider displayed at the top of the layers sidebar.
 */
export default function OpacitySlider({ value, onChange }: OpacitySliderProps) {
  return (
    <div
      className="flex-shrink-0 border-b-subtle"
      style={{ padding: "4px 8px 6px" }}
    >
      <div className="d-flex align-items-center" style={{ gap: 6 }}>
        <span style={{
          fontSize: 10, fontFamily: "monospace",
          color: "rgba(255,255,255,0.35)", flexShrink: 0, width: 28,
          textAlign: "right",
        }}>
          {Math.round(value * 100)}%
        </span>
        <Form.Range
          min={0} max={1} step={0.01}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          style={{ marginBottom: 0, flexGrow: 1 }}
        />
      </div>
    </div>
  );
}
