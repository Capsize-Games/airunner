import Form from "react-bootstrap/Form";

export default function PromptInput({
  label,
  value,
  onChange,
  placeholder,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  return (
    <Form.Group
      className="flex-grow-1 d-flex flex-column"
      style={{ minHeight: 0 }}
    >
      <Form.Label
        className="small flex-shrink-0"
        style={{ color: "var(--theme-text-secondary)" }}
      >
        {label}
      </Form.Label>
      <Form.Control
        as="textarea"
        className="flex-grow-1"
        style={{ resize: "none", minHeight: 0, width: "100%" }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </Form.Group>
  );
}
