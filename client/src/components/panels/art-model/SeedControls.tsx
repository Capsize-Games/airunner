import Form from "react-bootstrap/Form";
import LucideIcon from "../../shared/LucideIcon";

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
  return (
    <Form.Group className="mb-2">
      <Form.Label
        className="small"
        style={{ color: "var(--theme-text-secondary)" }}
      >
        Seed
      </Form.Label>
      <div className="d-flex align-items-center">
        <Form.Control
          size="sm"
          value={seed}
          readOnly={seedRandomized}
          disabled={loading}
          style={{
            flex: 1,
            background: "#1a1a2e",
            color: seedRandomized ? "#666" : "#c8c8c8",
            borderColor: seedRandomized ? "#555" : "#333",
            opacity: seedRandomized ? 0.5 : 1,
            borderTopRightRadius: 0,
            borderBottomRightRadius: 0,
          }}
          onChange={(e) => {
            const raw = e.target.value.replace(/[^0-9\-]/g, "");
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
            background: seedRandomized
              ? "var(--bs-primary)"
              : "#1a1a2e",
            border: "1px solid #444",
            borderLeft: "none",
            borderTopRightRadius: 4,
            borderBottomRightRadius: 4,
            borderTopLeftRadius: 0,
            borderBottomLeftRadius: 0,
            width: 30,
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
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
