import { useState } from "react";
import { saveToStorage } from "../art-model/ArtModelStorage";
import LucideIcon from "../../shared/LucideIcon";
import InfoItem from "./InfoItem";
import SliderWithSpinbox from "../SliderWithSpinbox";
import SeedInfoRow from "./SeedInfoRow";
import type { ArtOptionsResponse } from "../../../api/client";

interface GenerationInfoPanelProps {
  showInfo: boolean;
  onToggleShowInfo: () => void;
  version: string;
  modelPath: string;
  scheduler: string;
  steps: number;
  cfgScale: number;
  nSamples: number;
  imagesPerBatch: number;
  generationType: "txt2img" | "img2img" | "inpaint";
  seed: number;
  seedRandomized: boolean;
  genWidth: number;
  genHeight: number;
  activeLoras: { id: number; name: string }[];
  activeEmbeddings: { id: number; name: string }[];
  isMultiPrompt: boolean;
  artOptions: ArtOptionsResponse | null;
  onVersionChange: (v: string) => void;
  onModelChange: (m: string) => void;
  onSchedulerChange: (s: string) => void;
  onStepsChange: (v: number) => void;
  onCfgScaleChange: (v: number) => void;
  onNSamplesChange: (v: number) => void;
  onImagesPerBatchChange: (v: number) => void;
  onGenerationTypeChange: (v: "txt2img" | "img2img" | "inpaint") => void;
  onSeedChange: (v: number) => void;
  onToggleRandom: () => void;
  onGenWidthChange: (v: number) => void;
  onGenHeightChange: (v: number) => void;
  onToggleLoraPanel: (anchorRect: DOMRect) => void;
  onToggleEmbeddingsPanel: (anchorRect: DOMRect) => void;
  persistGen: (updates: Record<string, unknown>) => void;
  openDropdown: (field: string, anchorRect: DOMRect) => void;
  toggleGenSize: (anchorRect?: DOMRect) => void;
}

export default function GenerationInfoPanel(
  props: GenerationInfoPanelProps,
) {
  const {
    showInfo, onToggleShowInfo, version, modelPath, scheduler,
    steps, cfgScale, nSamples, imagesPerBatch, generationType,
    seed, seedRandomized, genWidth, genHeight,
    activeLoras, activeEmbeddings, isMultiPrompt, artOptions,
    onVersionChange, onModelChange, onSchedulerChange,
    onStepsChange, onCfgScaleChange, onNSamplesChange,
    onImagesPerBatchChange, onSeedChange, onToggleRandom,
    onGenWidthChange, onGenHeightChange,
    onToggleLoraPanel, onToggleEmbeddingsPanel,
    persistGen, openDropdown, toggleGenSize,
  } = props;

  const [focusedField, setFocusedField] = useState<string | null>(null);

  const toggleFocused = (field: string) =>
    setFocusedField((f) => (f === field ? null : field));

  const rectLabel = (el: HTMLElement) =>
    (el as HTMLElement).getBoundingClientRect();

  return (
    <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", flexShrink: 0 }}>
      <button type="button" onClick={onToggleShowInfo}
        style={{
          display: "flex", alignItems: "center", gap: 6, width: "100%",
          padding: "4px 10px", border: "none",
          background: "rgba(255,255,255,0.04)",
          color: "var(--theme-text-secondary)", cursor: "pointer",
          fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
          textTransform: "uppercase", opacity: 0.6,
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
          (e.currentTarget as HTMLButtonElement).style.opacity = "0.85";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.04)";
          (e.currentTarget as HTMLButtonElement).style.opacity = "0.6";
        }}
      >
        <LucideIcon name={showInfo ? "chevron-down" : "chevron-right"} size={10} />
        <span>Generation Settings</span>
      </button>
      {showInfo && (
        <div style={{ display: "flex", flexDirection: "column" }}>
          <InfoItem icon="sparkles" label="Model Version" value={version || "—"}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => openDropdown("version", rectLabel(e.currentTarget as HTMLElement))} />
          <InfoItem icon="sparkles" label="Model"
            value={modelPath ? (modelPath.split("/").pop()?.replace(/\.(gguf|bin|safetensors|pt|pth|ckpt|pkl|model)$/i, "") || modelPath) : "—"}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => openDropdown("model", rectLabel(e.currentTarget as HTMLElement))} />
          <InfoItem icon="sparkles" label="Scheduler" value={scheduler || "—"}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => openDropdown("scheduler", rectLabel(e.currentTarget as HTMLElement))} />

          <InfoItem icon="settings-2" label="Steps"
            editing={true}
            editor={<SliderWithSpinbox label="" value={steps} hideLabel
              min={1} max={150} step={1}
              onChange={(v) => { onStepsChange(v); saveToStorage("steps", v); persistGen({ steps: v }); }} />} />
          <InfoItem icon="settings-2" label="CFG"
            editing={true}
            editor={<SliderWithSpinbox label="" value={cfgScale} hideLabel
              min={1} max={30} step={0.1} displayAsFloat
              onChange={(v) => { onCfgScaleChange(v); saveToStorage("cfg_scale", v); persistGen({ cfg_scale: v }); }} />} />
          <InfoItem icon="settings-2" label="Samples"
            editing={true}
            editor={<SliderWithSpinbox label="" value={nSamples} hideLabel
              min={1} max={1000} step={1}
              onChange={(v) => { onNSamplesChange(v); saveToStorage("n_samples", v); persistGen({ n_samples: v }); }} />} />
          <InfoItem icon="settings-2" label="Batch"
            editing={true}
            editor={<SliderWithSpinbox label="" value={imagesPerBatch} hideLabel
              min={1} max={6} step={1}
              onChange={(v) => { onImagesPerBatchChange(v); saveToStorage("images_per_batch", v); persistGen({ images_per_batch: v }); }} />} />

          <InfoItem icon="image-plus" label="Gen type"
            value={generationType === "txt2img" ? "Text-to-image" : generationType === "img2img" ? "Image-to-image" : "Inpaint"}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => openDropdown("gentype", rectLabel(e.currentTarget as HTMLElement))} />

          <SeedInfoRow
            seed={seed} seedRandomized={seedRandomized}
            focusedField={focusedField}
            onToggleFocused={toggleFocused}
            onSeedChange={onSeedChange}
            onToggleRandom={onToggleRandom}
          />

          <InfoItem icon="ruler-dimension-line" label="Size"
            value={`${genWidth}×${genHeight}`}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => toggleGenSize(rectLabel(e.currentTarget as HTMLElement))} />

          <InfoItem icon="puzzle" label="LoRA"
            value={`${activeLoras.length} LoRA enabled`}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => onToggleLoraPanel(rectLabel(e.currentTarget as HTMLElement))} />

          <InfoItem icon="scan-text" label="Embeddings"
            value={isMultiPrompt ? `${activeEmbeddings.length} Embeddings enabled` : "Embeddings unavailable for Z-Image"}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={isMultiPrompt ? (e) => onToggleEmbeddingsPanel(rectLabel(e.currentTarget as HTMLElement)) : undefined} />
        </div>
      )}
    </div>
  );
}
