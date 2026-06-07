import { useState } from "react";
import Form from "react-bootstrap/Form";
import LucideIcon from "../shared/LucideIcon";

interface SliderWithSpinboxProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  displayAsFloat?: boolean;
  /** Default value for the reset button. When not set, no reset button is shown. */
  defaultValue?: number;
  onChange: (value: number) => void;
}

export default function SliderWithSpinbox({
  label,
  value,
  min,
  max,
  step,
  displayAsFloat = false,
  defaultValue,
  onChange,
}: SliderWithSpinboxProps) {
  const [hovered, setHovered] = useState(false);
  const [draftText, setDraftText] = useState<string | null>(null);
  const isChanged = defaultValue !== undefined && value !== defaultValue;

  const displayValue = displayAsFloat
    ? value.toFixed(2)
    : String(Math.round(value));

  const inputValue = draftText !== null ? draftText : displayValue;

  return (
    <Form.Group className="flex-fill">
      <Form.Label className="small" style={{ color: "var(--theme-text-secondary)" }}>
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
        <div style={{ display: "flex", flexShrink: 0 }}>
          <Form.Control
            size="sm"
            type="text"
            inputMode="decimal"
            value={inputValue}
            onChange={(e) => {
              const raw = e.target.value.replace(/[^0-9.\-]/g, "");
              setDraftText(raw);
              if (raw === "" || raw === "-" || raw.endsWith(".")) return;
              const v = Number(raw);
              if (isNaN(v)) return;
              onChange(Math.min(max, Math.max(min, v)));
            }}
            onBlur={() => {
              if (draftText !== null) {
                const v = Number(draftText.replace(/[^0-9.\-]/g, ""));
                if (draftText !== "" && !isNaN(v)) {
                  onChange(Math.min(max, Math.max(min, v)));
                }
                setDraftText(null);
              }
            }}
            style={{
              width: 48,
              background: "#1a1a2e",
              color: "var(--theme-text)",
              borderColor: "#333",
              textAlign: "right",
              borderTopRightRadius: defaultValue !== undefined ? 0 : undefined,
              borderBottomRightRadius: defaultValue !== undefined ? 0 : undefined,
            }}
          />
          {defaultValue !== undefined && (
            <button
              type="button"
              onMouseEnter={() => setHovered(true)}
              onMouseLeave={() => setHovered(false)}
              onClick={() => onChange(defaultValue)}
              disabled={!isChanged}
              title={`Reset to ${displayAsFloat ? defaultValue.toFixed(2) : defaultValue}`}
              style={{
                background: hovered && isChanged
                  ? "rgba(0,132,185,0.15)"
                  : "#1a1a2e",
                border: "1px solid #444",
                borderLeft: "none",
                borderTopRightRadius: 4,
                borderBottomRightRadius: 4,
                borderTopLeftRadius: 0,
                borderBottomLeftRadius: 0,
                width: 24,
                padding: 4,
                cursor: isChanged ? "pointer" : "default",
                opacity: isChanged ? 1 : 0.35,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <LucideIcon name="rotate-ccw-square" size={16} />
            </button>
          )}
        </div>
      </div>
    </Form.Group>
  );
}
