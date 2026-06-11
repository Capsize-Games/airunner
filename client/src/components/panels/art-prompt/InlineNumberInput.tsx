export default function InlineNumberInput({
  value,
  min,
  max,
  step,
  float,
  onChange,
  onClose,
}: {
  value: number;
  min: number;
  max: number;
  step?: number;
  float?: boolean;
  onChange: (v: number) => void;
  onClose: () => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <input
        type="number"
        className="art-no-spin"
        defaultValue={value}
        onBlur={(e) => {
          const v = float
            ? parseFloat(e.target.value)
            : parseInt(e.target.value, 10);
          if (!isNaN(v) && v >= min && v <= max) {
            onChange(v);
            onClose();
          }
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            const v = float
              ? parseFloat((e.target as HTMLInputElement).value)
              : parseInt((e.target as HTMLInputElement).value, 10);
            if (!isNaN(v) && v >= min && v <= max) {
              onChange(v);
              onClose();
            }
          }
        }}
        style={{
          height: 22,
          width: 56,
          background: "var(--theme-input-bg)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 4,
          color: "var(--theme-text)",
          fontSize: 10,
          textAlign: "center",
          padding: "0 4px",
        }}
        autoFocus
      />
      <span
        style={{
          fontSize: 9,
          color: "var(--theme-text-secondary)",
          opacity: 0.4,
        }}
      >
        (
        {float
          ? `${min.toFixed(1)}–${max.toFixed(1)}`
          : `${min}–${max}`}
        )
      </span>
    </div>
  );
}
