import Form from "react-bootstrap/Form";

export const CHECKBOX_FIELDS: { key: string; label: string }[] = [
  { key: "early_stopping", label: "Early Stopping" },
  { key: "do_sample", label: "Do Sample" },
  { key: "use_cache", label: "Use Cache" },
];

export default function CheckboxFields({
  collectValues,
  setOverride,
}: {
  collectValues: () => Record<string, unknown>;
  setOverride: (key: string, value: number | boolean) => void;
}) {
  return (
    <div className="d-flex gap-3 mb-2 flex-wrap">
      {CHECKBOX_FIELDS.map((f) => (
        <Form.Check
          key={f.key}
          type="switch"
          id={`llm-${f.key}`}
          label={
            <span style={{ color: "var(--theme-text-secondary)" }}>
              {f.label}
            </span>
          }
          checked={collectValues()[f.key] as boolean}
          onChange={(e) => setOverride(f.key, e.target.checked)}
        />
      ))}
    </div>
  );
}
