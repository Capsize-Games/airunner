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
      {label ? (
        <div
          style={{
            fontSize: 10,
            color: "var(--theme-text-secondary)",
            padding: "2px 8px",
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderBottom: "none",
            borderTopLeftRadius: 4,
            borderTopRightRadius: 4,
            flexShrink: 0,
            lineHeight: "16px",
            userSelect: "none",
          }}
        >
          {label}
        </div>
      ) : null}
      <Form.Control
        as="textarea"
        className="flex-grow-1"
        style={{
          resize: "none",
          minHeight: 0,
          width: "100%",
          ...(label
            ? { borderTopLeftRadius: 0, borderTopRightRadius: 0 }
            : {}),
        }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
      />
    </Form.Group>
  );
}
