import Form from "react-bootstrap/Form";

export default function VersionSelector({
  versions,
  value,
  loading,
  onChange,
}: {
  versions: { name: string }[];
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
        Version
      </Form.Label>
      <Form.Select
        size="sm"
        value={value}
        disabled={loading}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Version...</option>
        {versions.map((v) => (
          <option key={v.name} value={v.name}>
            {v.name}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}
