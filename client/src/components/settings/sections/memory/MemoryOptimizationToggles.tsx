import Form from "react-bootstrap/Form";

const OPTIMIZATION_TOGGLES: { key: string; label: string }[] = [
  { key: "use_accelerated_transformers", label: "Accelerated Transformers" },
  { key: "use_attention_slicing", label: "Attention Slicing" },
  { key: "use_enable_sequential_cpu_offload", label: "Sequential CPU offload" },
  { key: "enable_model_cpu_offload", label: "Model CPU offload" },
  { key: "use_last_channels", label: "Channels last memory format" },
  { key: "use_tf32", label: "TF32 precision" },
  { key: "use_enable_vae_slicing", label: "VAE Slicing" },
  { key: "use_tiled_vae", label: "Tile VAE" },
];

export default function MemoryOptimizationToggles({
  settings,
  onToggle,
}: {
  settings: Record<string, boolean>;
  onToggle: (key: string, value: boolean) => void;
}) {
  return (
    <div className="mb-3">
      <h6 className="small text-muted mb-2">
        Memory Optimization
      </h6>
      {OPTIMIZATION_TOGGLES.map(({ key, label }) => (
        <Form.Group key={key} className="mb-1">
          <Form.Check
            type="switch"
            label={label}
            checked={settings[key] ?? false}
            onChange={(e) => onToggle(key, e.target.checked)}
            className="small"
          />
        </Form.Group>
      ))}
    </div>
  );
}
