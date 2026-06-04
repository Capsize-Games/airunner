import Form from "react-bootstrap/Form";

interface MetadataFlags {
  prompt: boolean;
  negative_prompt: boolean;
  samples: boolean;
  model: boolean;
  model_branch: boolean;
  scale: boolean;
  seed: boolean;
  steps: boolean;
  iterations: boolean;
  scheduler: boolean;
  ddim_eta: boolean;
  strength: boolean;
  clip_skip: boolean;
  version: boolean;
  lora: boolean;
  embeddings: boolean;
  timestamp: boolean;
  controlnet: boolean;
  tome_sd: boolean;
  tome_ratio: boolean;
}

const METADATA_LABELS: Record<keyof MetadataFlags, string> = {
  prompt: "Prompt",
  negative_prompt: "Negative Prompt",
  samples: "Samples",
  model: "Model",
  model_branch: "Model Branch",
  scale: "Scale",
  seed: "Seed",
  steps: "Steps",
  iterations: "Iterations",
  scheduler: "Scheduler",
  ddim_eta: "DDIM ETA",
  strength: "Strength",
  clip_skip: "Clip Skip",
  version: "Version",
  lora: "LoRA",
  embeddings: "Embeddings",
  timestamp: "Timestamp",
  controlnet: "Controlnet",
  tome_sd: "ToMe SD",
  tome_ratio: "ToMe Ratio",
};

export default function MetadataCheckboxes({
  metadataFlags,
  onToggle,
}: {
  metadataFlags: MetadataFlags;
  onToggle: (key: keyof MetadataFlags, checked: boolean) => void;
}) {
  const metaKeys = Object.keys(METADATA_LABELS) as Array<keyof MetadataFlags>;

  return (
    <div
      className="border rounded p-2 mb-2"
      style={{ maxHeight: 280, overflowY: "auto" }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "2px 12px",
        }}
      >
        {metaKeys.map((key) => (
          <Form.Check
            key={key}
            type="switch"
            id={`meta-${key}`}
            label={METADATA_LABELS[key]}
            checked={metadataFlags[key]}
            onChange={(e) => onToggle(key, e.target.checked)}
            className="small"
          />
        ))}
      </div>
    </div>
  );
}
