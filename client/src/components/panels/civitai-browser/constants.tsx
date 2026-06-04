/** Constants for CivitAI browser filters, mirroring the PySide6 dialog. */

export const BASE_MODEL_OPTIONS = [
  { label: "SDXL 1.0", value: "SDXL 1.0" },
  { label: "Z-Image Turbo", value: "ZImageTurbo" },
] as const;

export const MODEL_TYPE_OPTIONS: Record<string, { label: string; value: string }[]> = {
  "SDXL 1.0": [
    { label: "Checkpoint", value: "Checkpoint" },
    { label: "LoRA", value: "LORA" },
    { label: "Embedding", value: "TextualInversion" },
  ],
  ZImageTurbo: [
    { label: "Checkpoint", value: "Checkpoint" },
  ],
};

export const ALL_MODEL_TYPES = [
  { label: "Checkpoint", value: "Checkpoint" },
  { label: "LoRA", value: "LORA" },
  { label: "Embedding", value: "TextualInversion" },
];
