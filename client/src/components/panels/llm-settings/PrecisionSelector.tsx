import Form from "react-bootstrap/Form";

export default function PrecisionSelector({
  precisionOptions,
  precision,
  onChange,
}: {
  precisionOptions: { label: string; value: string }[];
  precision: string;
  onChange: (value: string) => void;
}) {
  if (precisionOptions.length === 0) return null;

  return (
    <Form.Group className="mb-2">
      <Form.Label
        className="small"
        style={{ color: "var(--theme-text-secondary)" }}
      >
        Runtime Precision
      </Form.Label>
      <Form.Select
        size="sm"
        value={precision}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Default</option>
        {precisionOptions.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}
