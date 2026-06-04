import Form from "react-bootstrap/Form";

export default function ModelSelector({
  models,
  value,
  loading,
  hasVersion,
  onChange,
}: {
  models: { label: string; value: string }[];
  value: string;
  loading: boolean;
  hasVersion: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <Form.Group className="mb-2">
      <Form.Label
        className="small"
        style={{ color: "var(--theme-text-secondary)" }}
      >
        Model
      </Form.Label>
      <Form.Select
        size="sm"
        value={value}
        disabled={loading || !hasVersion || models.length === 0}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{!hasVersion ? "Version..." : "Model..."}</option>
        {models.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}
