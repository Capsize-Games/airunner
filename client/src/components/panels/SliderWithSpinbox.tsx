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
  /** Fixed pixel width for the label column so sibling sliders align. */
  labelWidth?: number;
  /** When true, the label column is hidden entirely. */
  hideLabel?: boolean;
  onChange: (value: number) => void;
}

const ITEM_H = 26;

export default function SliderWithSpinbox({
  label,
  value,
  min,
  max,
  step,
  displayAsFloat = false,
  defaultValue,
  labelWidth,
  hideLabel = false,
  onChange,
}: SliderWithSpinboxProps) {
  const [hovered, setHovered] = useState(false);
  const [draftText, setDraftText] = useState<string | null>(null);
  const isChanged = defaultValue !== undefined && value !== defaultValue;

  const displayValue = displayAsFloat
    ? value.toFixed(2)
    : String(Math.round(value));

  const inputValue = draftText !== null ? draftText : displayValue;

  const borderColor = "#444";
  const bgColor = "#1a1a2e";

  return (
    <div className="d-flex align-items-center" style={{ height: ITEM_H }}>
        {/* Label — attached left */}
        {!hideLabel && (
          <span
            style={{
              background: bgColor,
              border: `1px solid ${borderColor}`,
              borderTopLeftRadius: 4,
              borderBottomLeftRadius: 4,
              borderTopRightRadius: 0,
              borderBottomRightRadius: 0,
              padding: "0 6px",
              fontSize: 11,
              color: "var(--theme-text-secondary)",
              lineHeight: `${ITEM_H}px`,
              height: ITEM_H,
              flexShrink: 0,
              whiteSpace: "nowrap",
              boxSizing: "border-box",
              ...(labelWidth !== undefined && { width: labelWidth, minWidth: labelWidth }),
            }}
          >
            {label}
          </span>
        )}

        {/* Range slider — attached middle */}
        <div
          style={{
            flex: 1,
            height: ITEM_H,
            border: `1px solid ${borderColor}`,
            marginLeft: -1,
            display: "flex",
            alignItems: "center",
            padding: "0 6px",
            boxSizing: "border-box",
            background: bgColor,
          }}
        >
          <Form.Range
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            style={{
              width: "100%",
              display: "block",
              height: 4,
              cursor: "pointer",
              margin: 0,
              padding: 0,
            }}
          />
        </div>

        {/* Spinbox input + optional reset — attached right */}
        <div style={{ display: "flex", flexShrink: 0, marginLeft: -1 }}>
          <Form.Control
            size="sm"
            type="text"
            inputMode="decimal"
            value={inputValue}
            onChange={(e) => {
              const raw = e.target.value.replace(/[^0-9.-]/g, "");
              setDraftText(raw);
              if (raw === "" || raw === "-" || raw.endsWith(".")) return;
              const v = Number(raw);
              if (isNaN(v)) return;
              onChange(Math.min(max, Math.max(min, v)));
            }}
            onBlur={() => {
              if (draftText !== null) {
                const v = Number(draftText.replace(/[^0-9.-]/g, ""));
                if (draftText !== "" && !isNaN(v)) {
                  onChange(Math.min(max, Math.max(min, v)));
                }
                setDraftText(null);
              }
            }}
            style={{
              width: 48,
              height: ITEM_H,
              background: bgColor,
              color: "var(--theme-text)",
              border: `1px solid ${borderColor}`,
              textAlign: "right",
              borderTopRightRadius: defaultValue !== undefined ? 0 : 4,
              borderBottomRightRadius: defaultValue !== undefined ? 0 : 4,
              borderTopLeftRadius: 0,
              borderBottomLeftRadius: 0,
              boxSizing: "border-box",
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
                height: ITEM_H,
                width: 24,
                background: hovered && isChanged
                  ? "rgba(0,132,185,0.15)"
                  : bgColor,
                border: `1px solid ${borderColor}`,
                borderLeft: "none",
                borderTopRightRadius: 4,
                borderBottomRightRadius: 4,
                borderTopLeftRadius: 0,
                borderBottomLeftRadius: 0,
                marginLeft: -1,
                padding: 0,
                cursor: isChanged ? "pointer" : "default",
                opacity: isChanged ? 1 : 0.35,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                boxSizing: "border-box",
              }}
            >
              <LucideIcon name="rotate-ccw-square" size={14} />
            </button>
          )}
      </div>
    </div>
  );
}
