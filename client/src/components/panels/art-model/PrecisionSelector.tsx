import Form from "react-bootstrap/Form";

export default function PrecisionSelector({
  precisions,
  value,
  loading,
  onChange,
}: {
  precisions: { label: string; value: string }[];
  value: string;
  loading: boolean;
  onChange: (v: string) => void;
}) {
  return (
    <Form.Group className="mb-2">
      <Form.Label
        className="small"
        style={{ color: "var(--theme-text-secondary)" }}
      >
        Precision
      </Form.Label>
      <Form.Select
        size="sm"
        value={value}
        disabled={loading}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select precision...</option>
        {precisions.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}
