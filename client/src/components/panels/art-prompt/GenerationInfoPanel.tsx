import { useState } from "react";
import { saveToStorage } from "../art-model/ArtModelStorage";
import LucideIcon from "../../shared/LucideIcon";
import InfoItem from "./InfoItem";
import InlineNumberInput from "./InlineNumberInput";
import InlineSizeEditor from "./InlineSizeEditor";
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
  generationType: "txt2img" | "img2img";
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
  onGenerationTypeChange: (v: "txt2img" | "img2img") => void;
  onSeedChange: (v: number) => void;
  onToggleRandom: () => void;
  onGenWidthChange: (v: number) => void;
  onGenHeightChange: (v: number) => void;
  onToggleLoraPanel: () => void;
  onToggleEmbeddingsPanel: () => void;
  persistGen: (updates: Record<string, unknown>) => void;
  openDropdown: (field: string, anchorRect: DOMRect) => void;
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
    persistGen, openDropdown,
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
        <span>Generation Info</span>
      </button>
      {showInfo && (
        <div style={{ display: "flex", flexDirection: "column" }}>
          <InfoItem icon="sparkles" label="Model Version" value={version || "—"}
            onClick={(e) => openDropdown("version", rectLabel(e.currentTarget as HTMLElement))} />
          <InfoItem icon="sparkles" label="Model"
            value={modelPath ? (modelPath.split("/").pop()?.replace(/\.(gguf|bin|safetensors|pt|pth|ckpt|pkl|model)$/i, "") || modelPath) : "—"}
            onClick={(e) => openDropdown("model", rectLabel(e.currentTarget as HTMLElement))} />
          <InfoItem icon="sparkles" label="Scheduler" value={scheduler || "—"}
            onClick={(e) => openDropdown("scheduler", rectLabel(e.currentTarget as HTMLElement))} />

          <InfoItem icon="settings-2" label="Steps" value={String(steps)}
            editing={focusedField === "steps"}
            onClick={() => toggleFocused("steps")}
            editor={<InlineNumberInput value={steps} min={1} max={150}
              onChange={(v) => { onStepsChange(v); saveToStorage("steps", v); persistGen({ steps: v }); }}
              onClose={() => setFocusedField(null)} />} />

          <InfoItem icon="settings-2" label="CFG" value={String(cfgScale)}
            editing={focusedField === "cfg"}
            onClick={() => toggleFocused("cfg")}
            editor={<InlineNumberInput value={cfgScale} min={1} max={30} step={0.1} float
              onChange={(v) => { onCfgScaleChange(v); saveToStorage("cfg_scale", v); persistGen({ cfg_scale: v }); }}
              onClose={() => setFocusedField(null)} />} />

          <InfoItem icon="settings-2" label="Samples" value={String(nSamples)}
            editing={focusedField === "samples"}
            onClick={() => toggleFocused("samples")}
            editor={<InlineNumberInput value={nSamples} min={1} max={1000}
              onChange={(v) => { onNSamplesChange(v); saveToStorage("n_samples", v); persistGen({ n_samples: v }); }}
              onClose={() => setFocusedField(null)} />} />

          <InfoItem icon="settings-2" label="Batch" value={String(imagesPerBatch)}
            editing={focusedField === "batch"}
            onClick={() => toggleFocused("batch")}
            editor={<InlineNumberInput value={imagesPerBatch} min={1} max={6}
              onChange={(v) => { onImagesPerBatchChange(v); saveToStorage("images_per_batch", v); persistGen({ images_per_batch: v }); }}
              onClose={() => setFocusedField(null)} />} />

          <InfoItem icon="image-plus" label="Gen type"
            value={generationType === "txt2img" ? "Text-to-image" : "Image-to-image"}
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
            editing={focusedField === "size"}
            onClick={() => toggleFocused("size")}
            editor={<InlineSizeEditor w={genWidth} h={genHeight}
              onWChange={(v) => { onGenWidthChange(v); saveToStorage("gen_width", v); persistGen({ width: v }); }}
              onHChange={(v) => { onGenHeightChange(v); saveToStorage("gen_height", v); persistGen({ height: v }); }}
              onClose={() => setFocusedField(null)} />} />

          <InfoItem icon="puzzle" label="LoRA"
            value={`${activeLoras.length} LoRA enabled`}
            onClick={onToggleLoraPanel} />

          <InfoItem icon="scan-text" label="Embeddings"
            value={isMultiPrompt ? `${activeEmbeddings.length} Embeddings enabled` : "Embeddings unavailable for Z-Image"}
            onClick={isMultiPrompt ? onToggleEmbeddingsPanel : undefined} />
        </div>
      )}
    </div>
  );
}
