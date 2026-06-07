import SliderWithSpinbox from "../SliderWithSpinbox";

export const SLIDER_FIELDS: {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  float?: boolean;
}[] = [
  { key: "top_p", label: "Top P", min: 0, max: 1, step: 0.01, float: true },
  { key: "max_new_tokens", label: "Max New Tokens", min: 1, max: 32768, step: 1 },
  { key: "repetition_penalty", label: "Repetition Penalty", min: 0.01, max: 100, step: 0.01, float: true },
  { key: "min_length", label: "Min Length", min: 1, max: 2556, step: 1 },
  { key: "length_penalty", label: "Length Penalty", min: 0, max: 1, step: 0.01, float: true },
  { key: "num_beams", label: "Num Beams", min: 0, max: 100, step: 1 },
  { key: "ngram_size", label: "NGram Size", min: 0, max: 20, step: 1 },
  { key: "temperature", label: "Temperature", min: 0, max: 2, step: 0.01, float: true },
  { key: "sequences", label: "Sequences", min: 0, max: 100, step: 1 },
  { key: "top_k", label: "Top K", min: 0, max: 256, step: 1 },
];

export default function SliderFields({
  presets,
  activePresetRef,
  collectValues,
  setOverride,
}: {
  presets: { label: string; args: Record<string, unknown> }[];
  activePresetRef: React.MutableRefObject<string>;
  collectValues: () => Record<string, unknown>;
  setOverride: (key: string, value: number | boolean) => void;
}) {
  return (
    <>
      {SLIDER_FIELDS.map((f) => {
        const presetDefault = activePresetRef.current
          ? (presets.find(p => p.label === activePresetRef.current)
              ?.args?.[f.key] as number | undefined)
          : undefined;
        return (
          <div key={f.key} style={{ marginBottom: 4 }}>
            <SliderWithSpinbox
              label={f.label}
              value={collectValues()[f.key] as number}
              min={f.min}
              max={f.max}
              step={f.step}
              displayAsFloat={f.float}
              defaultValue={presetDefault}
              labelWidth={120}
              onChange={(v) => setOverride(f.key, v)}
            />
          </div>
        );
      })}
    </>
  );
}
