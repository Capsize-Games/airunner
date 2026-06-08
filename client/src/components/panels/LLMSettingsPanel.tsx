import { useState, useEffect, useCallback, useRef } from "react";
import {
  getSingleton,
  updateSingleton,
  getArtModelOptions,
  listLLMPresets,
} from "../../api/client";
import type {
  ResourceRecord,
} from "../../types/api";
import Form from "react-bootstrap/Form";
import ModelSelector from "../chat/ModelSelector";
import PresetSelector from "./llm-settings/PresetSelector";
import SliderFields from "./llm-settings/SliderFields";
import CheckboxFields from "./llm-settings/CheckboxFields";
import PrecisionSelector from "./llm-settings/PrecisionSelector";
import LucideIcon from "../shared/LucideIcon";

const DEFAULTS = {
  temperature: 0.7,
  max_new_tokens: 4096,
  top_p: 0.9,
  repetition_penalty: 1.1,
  min_length: 1,
  length_penalty: 1.0,
  num_beams: 1,
  ngram_size: 0,
  sequences: 1,
  top_k: 50,
  early_stopping: false,
  do_sample: true,
  use_cache: true,
};

interface Preset {
  label: string;
  args: Record<string, unknown>;
}

type Setters = Record<string, (v: number | boolean) => void>;

const STORAGE_KEY = "airunner_llm_overrides";
const UI_STORAGE_KEY = "airunner_llm_overrides_ui";

function loadOverrides(): Record<string, Record<string, unknown>> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw
      ? (JSON.parse(raw) as Record<string, Record<string, unknown>>)
      : {};
  } catch {
    return {};
  }
}

function saveOverrides(
  overrides: Record<string, Record<string, unknown>>,
) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
  } catch { /* quota */ }
}

function overridesForLabel(
  label: string,
): Record<string, unknown> {
  return loadOverrides()[label] ?? {};
}


export function LLMSettingsPanel() {
  const [temperature, setTemperature] = useState(DEFAULTS.temperature);
  const [maxTokens, setMaxTokens] = useState(DEFAULTS.max_new_tokens);
  const [precision, setPrecision] = useState("");
  const [precisionOptions, setPrecisionOptions] = useState<
    { label: string; value: string }[]
  >([]);
  const [loading, setLoading] = useState(true);

  const [topP, setTopP] = useState(DEFAULTS.top_p);
  const [repetitionPenalty, setRepetitionPenalty] = useState(
    DEFAULTS.repetition_penalty,
  );
  const [minLength, setMinLength] = useState(DEFAULTS.min_length);
  const [lengthPenalty, setLengthPenalty] = useState(
    DEFAULTS.length_penalty,
  );
  const [numBeams, setNumBeams] = useState(DEFAULTS.num_beams);
  const [ngramSize, setNgramSize] = useState(DEFAULTS.ngram_size);
  const [sequences, setSequences] = useState(DEFAULTS.sequences);
  const [topK, setTopK] = useState(DEFAULTS.top_k);
  const [earlyStopping, setEarlyStopping] = useState(
    DEFAULTS.early_stopping,
  );
  const [doSample, setDoSample] = useState(DEFAULTS.do_sample);
  const [useCache, setUseCache] = useState(DEFAULTS.use_cache);
  const [performConversationSummary, setPerformConversationSummary] =
    useState(false);
  const [summarizeAfterNTurns, setSummarizeAfterNTurns] = useState(8);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState(() => {
    try {
      const raw = localStorage.getItem(UI_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as {
          overrideEnabled?: boolean;
          selectedPreset?: string;
        };
        return parsed.selectedPreset ?? "";
      }
    } catch { /* ignore */ }
    return "";
  });
  const [overrideEnabled, setOverrideEnabled] = useState(() => {
    try {
      const raw = localStorage.getItem(UI_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as {
          overrideEnabled?: boolean;
          selectedPreset?: string;
        };
        return parsed.overrideEnabled ?? false;
      }
    } catch { /* ignore */ }
    return false;
  });
  const [overriddenLabels, setOverriddenLabels] = useState<Set<string>>(
    () => {
      const all = loadOverrides();
      return new Set(
        Object.keys(all).filter((k) => Object.keys(all[k]).length > 0),
      );
    },
  );
  const [selectKey, setSelectKey] = useState(0);
  const fetchedRef = useRef(false);
  const activePresetRef = useRef("");

  const setters: Setters = {
    top_p: (v) => setTopP(v as number),
    repetition_penalty: (v) => setRepetitionPenalty(v as number),
    min_length: (v) => setMinLength(v as number),
    length_penalty: (v) => setLengthPenalty(v as number),
    num_beams: (v) => setNumBeams(v as number),
    ngram_size: (v) => setNgramSize(v as number),
    temperature: (v) => setTemperature(v as number),
    max_new_tokens: (v) => setMaxTokens(v as number),
    sequences: (v) => setSequences(v as number),
    top_k: (v) => setTopK(v as number),
    early_stopping: (v) => setEarlyStopping(v as boolean),
    do_sample: (v) => setDoSample(v as boolean),
    use_cache: (v) => setUseCache(v as boolean),
  };

  const collectValues = useCallback(
    (): Record<string, unknown> => ({
      top_p: topP, repetition_penalty: repetitionPenalty,
      min_length: minLength, length_penalty: lengthPenalty,
      num_beams: numBeams, ngram_size: ngramSize,
      temperature: temperature, max_new_tokens: maxTokens,
      sequences: sequences, top_k: topK,
      early_stopping: earlyStopping, do_sample: doSample,
      use_cache: useCache,
      perform_conversation_summary: performConversationSummary,
      summarize_after_n_turns: summarizeAfterNTurns,
    }),
    [
      topP, repetitionPenalty, minLength, lengthPenalty,
      numBeams, ngramSize, temperature, maxTokens,
      sequences, topK, earlyStopping, doSample, useCache,
      performConversationSummary, summarizeAfterNTurns,
    ],
  );

  const persistOverrides = useCallback(() => {
    const label = activePresetRef.current;
    if (!label) return;
    const all = loadOverrides();
    all[label] = collectValues();
    saveOverrides(all);
    setOverriddenLabels(
      new Set(
        Object.keys(all).filter(
          (k) => Object.keys(all[k]).length > 0,
        ),
      ),
    );
    setSelectKey((n) => n + 1);
  }, [collectValues]);

  const applyValues = useCallback(
    (args: Record<string, unknown>) => {
      const v = (key: string) => args[key];
      setTopP((v("top_p") as number) ?? DEFAULTS.top_p);
      setRepetitionPenalty(
        (v("repetition_penalty") as number) ??
          DEFAULTS.repetition_penalty,
      );
      setMinLength((v("min_length") as number) ?? DEFAULTS.min_length);
      setLengthPenalty(
        (v("length_penalty") as number) ?? DEFAULTS.length_penalty,
      );
      setNumBeams((v("num_beams") as number) ?? DEFAULTS.num_beams);
      setNgramSize((v("ngram_size") as number) ?? DEFAULTS.ngram_size);
      setTemperature(
        (v("temperature") as number) ?? DEFAULTS.temperature,
      );
      setMaxTokens(
        (v("max_new_tokens") as number) ?? DEFAULTS.max_new_tokens,
      );
      setSequences((v("sequences") as number) ?? DEFAULTS.sequences);
      setTopK((v("top_k") as number) ?? DEFAULTS.top_k);
      setEarlyStopping(
        (v("early_stopping") as boolean) ?? DEFAULTS.early_stopping,
      );
      setDoSample(
        (v("do_sample") as boolean) ?? DEFAULTS.do_sample,
      );
      setUseCache(
        (v("use_cache") as boolean) ?? DEFAULTS.use_cache,
      );
      setPerformConversationSummary(
        (v("perform_conversation_summary") as boolean) ?? false,
      );
      setSummarizeAfterNTurns(
        (v("summarize_after_n_turns") as number) ?? 8,
      );
    },
    [],
  );

  const fetchAdvanced = useCallback(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    getSingleton("LLMGeneratorSettings")
      .then((r: ResourceRecord) => {
        setTemperature(Number(r.temperature ?? DEFAULTS.temperature));
        setMaxTokens(
          Number(r.max_new_tokens ?? DEFAULTS.max_new_tokens),
        );
        setPrecision(String(r.dtype ?? ""));
        setTopP(Number(r.top_p ?? DEFAULTS.top_p));
        setRepetitionPenalty(
          Number(r.repetition_penalty ?? DEFAULTS.repetition_penalty),
        );
        setMinLength(Number(r.min_length ?? DEFAULTS.min_length));
        setLengthPenalty(
          Number(r.length_penalty ?? DEFAULTS.length_penalty),
        );
        setNumBeams(Number(r.num_beams ?? DEFAULTS.num_beams));
        setNgramSize(Number(r.ngram_size ?? DEFAULTS.ngram_size));
        setSequences(Number(r.sequences ?? DEFAULTS.sequences));
        setTopK(Number(r.top_k ?? DEFAULTS.top_k));
        setEarlyStopping(
          r.early_stopping === true || r.early_stopping === "true",
        );
        setDoSample(r.do_sample === true || r.do_sample === "true");
        setUseCache(r.use_cache === true || r.use_cache === "true");
        setPerformConversationSummary(
          r.perform_conversation_summary === true ||
            r.perform_conversation_summary === "true",
        );
        setSummarizeAfterNTurns(
          Number(r.summarize_after_n_turns ?? 8),
        );
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    getArtModelOptions()
      .then((opts) => setPrecisionOptions(opts.precisions ?? []))
      .catch(() => {});
    listLLMPresets()
      .then((p) => setPresets(p))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchAdvanced();
  }, [fetchAdvanced]);

  useEffect(() => {
    if (presets.length === 0 || !selectedPreset) return;
    const preset = presets.find((p) => p.label === selectedPreset);
    if (!preset) return;
    activePresetRef.current = selectedPreset;
    const merged = { ...preset.args, ...overridesForLabel(selectedPreset) };
    applyValues(merged);
    persist(merged);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [presets.length > 0]);

  const persist = useCallback(
    (updates: Record<string, unknown>) => {
      updateSingleton("LLMGeneratorSettings", updates).catch(() => {});
    },
    [],
  );

  const setOverride = useCallback(
    (key: string, value: number | boolean) => {
      setters[key](value);
      if (activePresetRef.current) {
        const all = loadOverrides();
        const label = activePresetRef.current;
        const preset = presets.find(p => p.label === label);
        const presetDefault = preset?.args?.[key];
        const overridesForLabel = { ...(all[label] ?? {}) };
        if (presetDefault !== undefined && presetDefault === value) {
          delete overridesForLabel[key];
        } else {
          overridesForLabel[key] = value;
        }
        if (Object.keys(overridesForLabel).length === 0) {
          delete all[label];
        } else {
          all[label] = overridesForLabel;
        }
        saveOverrides(all);
        setOverriddenLabels(
          new Set(
            Object.keys(all).filter(
              (k) => Object.keys(all[k]).length > 0,
            ),
          ),
        );
        setSelectKey((n) => n + 1);
      }
      persist({ [key]: value });
    },
    [persist, presets],
  );

  const handlePresetChange = useCallback(
    (label: string) => {
      persistOverrides();
      setSelectedPreset(label);
      activePresetRef.current = label;
      const preset = presets.find((p) => p.label === label);
      if (!preset) return;
      const merged = { ...preset.args, ...overridesForLabel(label) };
      applyValues(merged);
      persist(merged);
    },
    [presets, persistOverrides, applyValues, persist],
  );

  const resetToDefaults = useCallback(() => {
    const label = activePresetRef.current;
    if (!label) return;
    const all = loadOverrides();
    delete all[label];
    saveOverrides(all);
    setOverriddenLabels((prev) => {
      const next = new Set(prev);
      next.delete(label);
      return next;
    });
    setSelectKey((n) => n + 1);
    const preset = presets.find((p) => p.label === label);
    if (preset) {
      applyValues(preset.args);
      persist(preset.args);
    }
  }, [presets, applyValues, persist]);

  const resetAllToDefaults = useCallback(() => {
    saveOverrides({});
    setOverriddenLabels(new Set());
    setSelectKey((n) => n + 1);
    if (selectedPreset) {
      const preset = presets.find((p) => p.label === selectedPreset);
      if (preset) {
        applyValues(preset.args);
        persist(preset.args);
      }
    }
  }, [presets, selectedPreset, applyValues, persist]);

  const handlePrecisionChange = (value: string) => {
    setPrecision(value);
    persist({ dtype: value });
  };

  if (loading) {
    return (
      <div className="p-2 small" style={{ color: "var(--theme-text-secondary)" }}>
        Loading...
      </div>
    );
  }

  return (
    <div className="p-2">
      <h6 style={{ color: "var(--theme-text-secondary)" }} className="mb-2">
        LLM Settings
      </h6>
      <ModelSelector />

      <div
        className="p-2 mt-2"
        style={{ border: "1px solid #333", borderRadius: 6 }}
      >
        <Form.Check
          type="switch"
          id="llm-override-toggle"
          label={
            <span style={{ color: "var(--theme-text-secondary)", fontWeight: 600 }}>
              Override LLM Settings
            </span>
          }
          checked={overrideEnabled}
          onChange={(e) => setOverrideEnabled(e.target.checked)}
        />

        {overrideEnabled && (
          <>
            <PresetSelector
              presets={presets}
              overriddenLabels={overriddenLabels}
              selectedPreset={selectedPreset}
              overrideEnabled={overrideEnabled}
              selectKey={selectKey}
              handlePresetChange={handlePresetChange}
            />

            {selectedPreset !== "" && (
              <>
                <SliderFields
                  presets={presets}
                  activePresetRef={activePresetRef}
                  collectValues={collectValues}
                  setOverride={setOverride}
                />

                <CheckboxFields
                  collectValues={collectValues}
                  setOverride={setOverride}
                />

                <PrecisionSelector
                  precisionOptions={precisionOptions}
                  precision={precision}
                  onChange={handlePrecisionChange}
                />

                <div
                  className="p-2 mt-2"
                  style={{
                    border: "1px solid #333",
                    borderRadius: 6,
                  }}
                >
                  <span
                    style={{
                      color: "var(--theme-text-secondary)",
                      fontWeight: 600,
                      fontSize: "0.85rem",
                      display: "block",
                      marginBottom: 8,
                    }}
                  >
                    Conversation Summarization
                  </span>
                  <Form.Check
                    type="switch"
                    id="llm-perform-summary"
                    label={
                      <span style={{ color: "var(--theme-text-secondary)" }}>
                        Auto-summarize long conversations
                      </span>
                    }
                    checked={performConversationSummary}
                    onChange={(e) => {
                      setPerformConversationSummary(e.target.checked);
                      persist({
                        perform_conversation_summary: e.target.checked,
                      });
                    }}
                  />
                  {performConversationSummary && (
                    <Form.Group className="mt-2">
                      <Form.Label
                        style={{
                          color: "var(--theme-text-secondary)",
                          fontSize: "0.8rem",
                        }}
                      >
                        Summarize after{" "}
                        <strong>{summarizeAfterNTurns}</strong>{" "}
                        conversation turns
                      </Form.Label>
                      <Form.Range
                        min={2}
                        max={50}
                        step={1}
                        value={summarizeAfterNTurns}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          setSummarizeAfterNTurns(v);
                          persist({
                            summarize_after_n_turns: v,
                          });
                        }}
                        style={{ accentColor: "var(--theme-primary)" }}
                      />
                    </Form.Group>
                  )}
                </div>

                <div className="d-flex gap-2 mt-1">
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary flex-fill"
                    onClick={resetToDefaults}
                    title="Reset the current preset to its default values"
                    style={{
                      color: "var(--theme-text-secondary)",
                      borderColor: "#444",
                    }}
                  >
                    <LucideIcon
                      name="rotate-ccw-square"
                      size={14}
                      className="me-1"
                    />
                    Reset {selectedPreset}
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary flex-fill"
                    onClick={resetAllToDefaults}
                    title="Reset all presets to their default values"
                    style={{
                      color: "var(--theme-text-secondary)",
                      borderColor: "#444",
                    }}
                  >
                    <LucideIcon
                      name="rotate-ccw-square"
                      size={14}
                      className="me-1"
                    />
                    Reset All
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
