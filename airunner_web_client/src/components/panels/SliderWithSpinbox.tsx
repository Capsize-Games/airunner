import Form from "react-bootstrap/Form";

interface SliderWithSpinboxProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  displayAsFloat?: boolean;
  onChange: (value: number) => void;
}

export default function SliderWithSpinbox({
  label,
  value,
  min,
  max,
  step,
  displayAsFloat = false,
  onChange,
}: SliderWithSpinboxProps) {
  const displayValue = displayAsFloat
    ? value.toFixed(2)
    : String(Math.round(value));

  return (
    <Form.Group className="flex-fill">
      <Form.Label className="small" style={{ color: "#a0a0a8" }}>
        {label}
      </Form.Label>
      <div className="d-flex gap-2 align-items-center">
        <Form.Range
          className="flex-grow-1"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        <Form.Control
          size="sm"
          type="text"
          inputMode="decimal"
          value={displayValue}
          onChange={(e) => {
            const raw = e.target.value.replace(/[^0-9.\-]/g, "");
            if (raw === "") return;
            let v = Number(raw);
            if (isNaN(v)) return;
            v = Math.min(max, Math.max(min, v));
            onChange(v);
          }}
          style={{
            width: 88,
            background: "#1a1a2e",
            color: "#c8c8c8",
            borderColor: "#333",
            textAlign: "right",
          }}
        />
      </div>
    </Form.Group>
  );
}
