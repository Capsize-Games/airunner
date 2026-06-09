import { useState } from "react";
import { updateSingleton } from "../../../api/client";
import ArtModelSliders from "../art-model/ArtModelSliders";
import {
  saveToStorage,
  loadFromStorage,
} from "../art-model/ArtModelStorage";

export default function ArtPromptBottomToolbar() {
  const [nSamples, setNSamples] = useState(
    loadFromStorage("n_samples", 1),
  );
  const [imagesPerBatch, setImagesPerBatch] = useState(
    loadFromStorage("images_per_batch", 1),
  );
  const [steps, setSteps] = useState(loadFromStorage("steps", 20));
  const [cfgScale, setCfgScale] = useState(
    loadFromStorage("cfg_scale", 7.5),
  );

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("GeneratorSettings", updates).catch(() => {});
  };

  return (
    <div
      className="bg-theme-panel flex-shrink-0 border-t-subtle"
      style={{ padding: "4px 8px" }}
    >
      <ArtModelSliders
        nSamples={nSamples}
        imagesPerBatch={imagesPerBatch}
        steps={steps}
        cfgScale={cfgScale}
        onNSamplesChange={(v) => {
          setNSamples(v);
          saveToStorage("n_samples", v);
          persist({ n_samples: v });
        }}
        onImagesPerBatchChange={(v) => {
          setImagesPerBatch(v);
          saveToStorage("images_per_batch", v);
          persist({ images_per_batch: v });
        }}
        onStepsChange={(v) => {
          setSteps(v);
          saveToStorage("steps", v);
          persist({ steps: v });
        }}
        onCfgScaleChange={(v) => {
          setCfgScale(v);
          saveToStorage("cfg_scale", v);
          persist({ cfg_scale: v });
        }}
      />
    </div>
  );
}
