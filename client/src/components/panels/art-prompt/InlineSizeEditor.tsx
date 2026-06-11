export default function InlineSizeEditor({
  w,
  h,
  onWChange,
  onHChange,
  onClose,
}: {
  w: number;
  h: number;
  onWChange: (v: number) => void;
  onHChange: (v: number) => void;
  onClose: () => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span
        style={{
          fontSize: 9,
          color: "var(--theme-text-secondary)",
        }}
      >
        W
      </span>
      <input
        type="number"
        className="art-no-spin"
        defaultValue={w}
        onBlur={(e) => {
          const v = Math.max(64, Math.min(2048, Number(e.target.value)));
          if (!isNaN(v)) onWChange(v);
          onClose();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            const v = Math.max(
              64,
              Math.min(2048, Number((e.target as HTMLInputElement).value)),
            );
            if (!isNaN(v)) {
              onWChange(v);
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
        }}
      >
        H
      </span>
      <input
        type="number"
        className="art-no-spin"
        defaultValue={h}
        onBlur={(e) => {
          const v = Math.max(64, Math.min(2048, Number(e.target.value)));
          if (!isNaN(v)) onHChange(v);
          onClose();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            const v = Math.max(
              64,
              Math.min(2048, Number((e.target as HTMLInputElement).value)),
            );
            if (!isNaN(v)) {
              onHChange(v);
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
      />
    </div>
  );
}
