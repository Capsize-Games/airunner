import Form from "react-bootstrap/Form";
import LucideIcon from "../../shared/LucideIcon";

const ITEM_H = 30;

export default function SeedControls({
  seed,
  seedRandomized,
  loading,
  onSeedChange,
  onToggleRandom,
}: {
  seed: number;
  seedRandomized: boolean;
  loading: boolean;
  onSeedChange: (v: number) => void;
  onToggleRandom: () => void;
}) {
  const borderColor = seedRandomized ? "#555" : "#444";
  const bgColor = "#1a1a2e";

  return (
    <Form.Group className="mb-2">
      <div className="d-flex align-items-center">
        <span
          style={{
            background: bgColor,
            border: `1px solid ${borderColor}`,
            borderTopLeftRadius: 4,
            borderBottomLeftRadius: 4,
            borderTopRightRadius: 0,
            borderBottomRightRadius: 0,
            padding: "0 8px",
            fontSize: 11,
            color: "var(--theme-text-secondary)",
            lineHeight: `${ITEM_H}px`,
            height: ITEM_H,
            flexShrink: 0,
            whiteSpace: "nowrap",
            boxSizing: "border-box",
          }}
        >
          Seed
        </span>
        <Form.Control
          size="sm"
          value={seed}
          readOnly={seedRandomized}
          disabled={loading}
          style={{
            flex: 1,
            height: ITEM_H,
            background: bgColor,
            color: seedRandomized ? "#666" : "#c8c8c8",
            border: `1px solid ${borderColor}`,
            borderRadius: 0,
            opacity: seedRandomized ? 0.5 : 1,
            marginLeft: -1,
            boxSizing: "border-box",
          }}
          onChange={(e) => {
            const raw = e.target.value.replace(/[^0-9-]/g, "");
            if (raw === "") return;
            const v = Number(raw);
            if (isNaN(v)) return;
            onSeedChange(v);
          }}
        />
        <button
          type="button"
          className="btn btn-sm p-1"
          onClick={onToggleRandom}
          title={
            seedRandomized
              ? "Use a fixed seed"
              : "Randomize seed on each generation"
          }
          style={{
            height: ITEM_H,
            width: 30,
            background: seedRandomized
              ? "var(--bs-primary)"
              : bgColor,
            border: `1px solid ${borderColor}`,
            borderTopRightRadius: 4,
            borderBottomRightRadius: 4,
            borderTopLeftRadius: 0,
            borderBottomLeftRadius: 0,
            marginLeft: -1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            boxSizing: "border-box",
            padding: 0,
          }}
        >
          <LucideIcon
            name="dices"
            size={16}
            className={seedRandomized ? "icon-white" : "icon-muted"}
          />
        </button>
      </div>
    </Form.Group>
  );
}
