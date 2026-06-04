import Form from "react-bootstrap/Form";

const UI_STORAGE_KEY = "airunner_llm_overrides_ui";

export default function PresetSelector({
  presets,
  overriddenLabels,
  selectedPreset,
  overrideEnabled,
  selectKey,
  handlePresetChange,
}: {
  presets: { label: string; args: Record<string, unknown> }[];
  overriddenLabels: Set<string>;
  selectedPreset: string;
  overrideEnabled: boolean;
  selectKey: number;
  handlePresetChange: (label: string) => void;
}) {
  if (presets.length === 0) return null;

  return (
    <Form.Group className="mb-2">
      <Form.Label
        className="small"
        style={{ color: "var(--theme-text-secondary)" }}
      >
        Preset
      </Form.Label>
      <Form.Select
        size="sm"
        key={selectKey}
        value={selectedPreset}
        onChange={(e) => {
          handlePresetChange(e.target.value);
          try {
            localStorage.setItem(
              UI_STORAGE_KEY,
              JSON.stringify({
                overrideEnabled,
                selectedPreset: e.target.value,
              }),
            );
          } catch { /* quota */ }
        }}
      >
        <option value="">Select a preset...</option>
        {presets.map((p) => (
          <option key={p.label} value={p.label}>
            {overriddenLabels.has(p.label) ? "● " : ""}
            {p.label}
          </option>
        ))}
      </Form.Select>
    </Form.Group>
  );
}
