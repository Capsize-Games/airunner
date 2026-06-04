import SliderWithSpinbox from "../SliderWithSpinbox";

export interface ArtModelSlidersProps {
  nSamples: number;
  imagesPerBatch: number;
  steps: number;
  cfgScale: number;
  width: number;
  height: number;
  onNSamplesChange: (v: number) => void;
  onImagesPerBatchChange: (v: number) => void;
  onStepsChange: (v: number) => void;
  onCfgScaleChange: (v: number) => void;
  onWidthChange: (v: number) => void;
  onHeightChange: (v: number) => void;
}

export default function ArtModelSliders({
  nSamples,
  imagesPerBatch,
  steps,
  cfgScale,
  width,
  height,
  onNSamplesChange,
  onImagesPerBatchChange,
  onStepsChange,
  onCfgScaleChange,
  onWidthChange,
  onHeightChange,
}: ArtModelSlidersProps) {
  return (
    <>
      <SliderWithSpinbox
        label="Samples"
        value={nSamples}
        min={1}
        max={1000}
        step={1}
        defaultValue={1}
        onChange={onNSamplesChange}
      />
      <SliderWithSpinbox
        label="Batch"
        value={imagesPerBatch}
        min={1}
        max={6}
        step={1}
        defaultValue={1}
        onChange={onImagesPerBatchChange}
      />
      <SliderWithSpinbox
        label="Steps"
        value={steps}
        min={1}
        max={150}
        step={1}
        defaultValue={20}
        onChange={onStepsChange}
      />
      <SliderWithSpinbox
        label="CFG"
        value={cfgScale}
        min={1}
        max={30}
        step={0.5}
        displayAsFloat
        defaultValue={7.5}
        onChange={onCfgScaleChange}
      />
      <SliderWithSpinbox
        label="Width"
        value={width}
        min={64}
        max={4096}
        step={64}
        defaultValue={1024}
        onChange={onWidthChange}
      />
      <SliderWithSpinbox
        label="Height"
        value={height}
        min={64}
        max={4096}
        step={64}
        defaultValue={1024}
        onChange={onHeightChange}
      />
    </>
  );
}
