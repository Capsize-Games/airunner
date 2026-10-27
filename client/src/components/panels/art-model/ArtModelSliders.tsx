import SliderWithSpinbox from "../SliderWithSpinbox";

export interface ArtModelSlidersProps {
  nSamples: number;
  imagesPerBatch: number;
  steps: number;
  cfgScale: number;
  onNSamplesChange: (v: number) => void;
  onImagesPerBatchChange: (v: number) => void;
  onStepsChange: (v: number) => void;
  onCfgScaleChange: (v: number) => void;
}

export default function ArtModelSliders({
  nSamples,
  imagesPerBatch,
  steps,
  cfgScale,
  onNSamplesChange,
  onImagesPerBatchChange,
  onStepsChange,
  onCfgScaleChange,
}: ArtModelSlidersProps) {
  const slider = (
    label: string,
    value: number,
    min: number,
    max: number,
    step: number,
    onChange: (v: number) => void,
    opts?: { displayAsFloat?: boolean; defaultVal?: number },
  ) => (
    <SliderWithSpinbox
      key={label}
      label={label}
      value={value}
      min={min}
      max={max}
      step={step}
      defaultValue={opts?.defaultVal ?? min}
      displayAsFloat={opts?.displayAsFloat}
      labelWidth={52}
      onChange={onChange}
    />
  );

  return (
    <div className="d-flex flex-column gap-1">
      {slider("Samples", nSamples, 1, 1000, 1, onNSamplesChange, { defaultVal: 1 })}
      {slider("Batch", imagesPerBatch, 1, 6, 1, onImagesPerBatchChange, { defaultVal: 1 })}
      {slider("Steps", steps, 1, 150, 1, onStepsChange, { defaultVal: 20 })}
      {slider("CFG", cfgScale, 1, 30, 0.01, onCfgScaleChange, { defaultVal: 7.5, displayAsFloat: true })}
    </div>
  );
}
