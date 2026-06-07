import Form from "react-bootstrap/Form";

export default function SchedulerSelector({
  schedulers,
  value,
  loading,
  hasVersion,
  onChange,
}: {
  schedulers: { label: string; value: string }[];
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
        Scheduler
      </Form.Label>
      <Form.Select
        size="sm"
        value={value}
        disabled={loading || !hasVersion}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select scheduler...</option>
        {schedulers.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}
