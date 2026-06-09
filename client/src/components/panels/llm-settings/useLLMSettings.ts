import { useState, useEffect, useCallback, useRef } from "react";
import {
  getSingleton, updateSingleton, getArtModelOptions, listLLMPresets,
} from "../../../api/client";
import type { ResourceRecord } from "../../../types/api";

export const DEFAULTS = {
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

export interface Preset {
  label: string;
  args: Record<string, unknown>;
}

const STORAGE_KEY = "airunner_llm_overrides";
const UI_STORAGE_KEY = "airunner_llm_overrides_ui";

function loadOverrides(): Record<string, Record<string, unknown>> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, Record<string, unknown>>) : {};
  } catch { return {}; }
}

function saveOverrides(overrides: Record<string, Record<string, unknown>>) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides)); }
  catch { /* quota */ }
}

function overridesForLabel(label: string): Record<string, unknown> {
  return loadOverrides()[label] ?? {};
}

function computeOverriddenLabels(all: Record<string, Record<string, unknown>>) {
  return new Set(Object.keys(all).filter((k) => Object.keys(all[k]).length > 0));
}

export function useLLMSettings() {
  const [temperature, setTemperature] = useState(DEFAULTS.temperature);
  const [maxTokens, setMaxTokens] = useState(DEFAULTS.max_new_tokens);
  const [precision, setPrecision] = useState("");
  const [precisionOptions, setPrecisionOptions] = useState<{ label: string; value: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [topP, setTopP] = useState(DEFAULTS.top_p);
  const [repetitionPenalty, setRepetitionPenalty] = useState(DEFAULTS.repetition_penalty);
  const [minLength, setMinLength] = useState(DEFAULTS.min_length);
  const [lengthPenalty, setLengthPenalty] = useState(DEFAULTS.length_penalty);
  const [numBeams, setNumBeams] = useState(DEFAULTS.num_beams);
  const [ngramSize, setNgramSize] = useState(DEFAULTS.ngram_size);
  const [sequences, setSequences] = useState(DEFAULTS.sequences);
  const [topK, setTopK] = useState(DEFAULTS.top_k);
  const [earlyStopping, setEarlyStopping] = useState(DEFAULTS.early_stopping);
  const [doSample, setDoSample] = useState(DEFAULTS.do_sample);
  const [useCache, setUseCache] = useState(DEFAULTS.use_cache);
  const [performConversationSummary, setPerformConversationSummary] = useState(false);
  const [summarizeAfterNTurns, setSummarizeAfterNTurns] = useState(8);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState(() => {
    try {
      const raw = localStorage.getItem(UI_STORAGE_KEY);
      if (raw) return (JSON.parse(raw) as { selectedPreset?: string }).selectedPreset ?? "";
    } catch { /* */ }
    return "";
  });
  const [overrideEnabled, setOverrideEnabled] = useState(() => {
    try {
      const raw = localStorage.getItem(UI_STORAGE_KEY);
      if (raw) return (JSON.parse(raw) as { overrideEnabled?: boolean }).overrideEnabled ?? false;
    } catch { /* */ }
    return false;
  });
  const [overriddenLabels, setOverriddenLabels] = useState<Set<string>>(
    () => computeOverriddenLabels(loadOverrides()),
  );
  const [selectKey, setSelectKey] = useState(0);

  const fetchedRef = useRef(false);
  const activePresetRef = useRef("");

  const setters: Record<string, (v: number | boolean) => void> = {
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

  const collectValues = useCallback((): Record<string, unknown> => ({
    top_p: topP, repetition_penalty: repetitionPenalty,
    min_length: minLength, length_penalty: lengthPenalty,
    num_beams: numBeams, ngram_size: ngramSize,
    temperature, max_new_tokens: maxTokens,
    sequences, top_k: topK,
    early_stopping: earlyStopping, do_sample: doSample, use_cache: useCache,
    perform_conversation_summary: performConversationSummary,
    summarize_after_n_turns: summarizeAfterNTurns,
  }), [
    topP, repetitionPenalty, minLength, lengthPenalty, numBeams, ngramSize,
    temperature, maxTokens, sequences, topK, earlyStopping, doSample, useCache,
    performConversationSummary, summarizeAfterNTurns,
  ]);

  const persist = useCallback((updates: Record<string, unknown>) => {
    updateSingleton("LLMGeneratorSettings", updates).catch(() => {});
  }, []);

  const applyValues = useCallback((args: Record<string, unknown>) => {
    const v = (key: string) => args[key];
    setTopP((v("top_p") as number) ?? DEFAULTS.top_p);
    setRepetitionPenalty((v("repetition_penalty") as number) ?? DEFAULTS.repetition_penalty);
    setMinLength((v("min_length") as number) ?? DEFAULTS.min_length);
    setLengthPenalty((v("length_penalty") as number) ?? DEFAULTS.length_penalty);
    setNumBeams((v("num_beams") as number) ?? DEFAULTS.num_beams);
    setNgramSize((v("ngram_size") as number) ?? DEFAULTS.ngram_size);
    setTemperature((v("temperature") as number) ?? DEFAULTS.temperature);
    setMaxTokens((v("max_new_tokens") as number) ?? DEFAULTS.max_new_tokens);
    setSequences((v("sequences") as number) ?? DEFAULTS.sequences);
    setTopK((v("top_k") as number) ?? DEFAULTS.top_k);
    setEarlyStopping((v("early_stopping") as boolean) ?? DEFAULTS.early_stopping);
    setDoSample((v("do_sample") as boolean) ?? DEFAULTS.do_sample);
    setUseCache((v("use_cache") as boolean) ?? DEFAULTS.use_cache);
    setPerformConversationSummary((v("perform_conversation_summary") as boolean) ?? false);
    setSummarizeAfterNTurns((v("summarize_after_n_turns") as number) ?? 8);
  }, []);

  const persistOverrides = useCallback(() => {
    const label = activePresetRef.current;
    if (!label) return;
    const all = loadOverrides();
    all[label] = collectValues();
    saveOverrides(all);
    setOverriddenLabels(computeOverriddenLabels(all));
    setSelectKey((n) => n + 1);
  }, [collectValues]);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    getSingleton("LLMGeneratorSettings")
      .then((r: ResourceRecord) => {
        setTemperature(Number(r.temperature ?? DEFAULTS.temperature));
        setMaxTokens(Number(r.max_new_tokens ?? DEFAULTS.max_new_tokens));
        setPrecision(String(r.dtype ?? ""));
        setTopP(Number(r.top_p ?? DEFAULTS.top_p));
        setRepetitionPenalty(Number(r.repetition_penalty ?? DEFAULTS.repetition_penalty));
        setMinLength(Number(r.min_length ?? DEFAULTS.min_length));
        setLengthPenalty(Number(r.length_penalty ?? DEFAULTS.length_penalty));
        setNumBeams(Number(r.num_beams ?? DEFAULTS.num_beams));
        setNgramSize(Number(r.ngram_size ?? DEFAULTS.ngram_size));
        setSequences(Number(r.sequences ?? DEFAULTS.sequences));
        setTopK(Number(r.top_k ?? DEFAULTS.top_k));
        setEarlyStopping(r.early_stopping === true || r.early_stopping === "true");
        setDoSample(r.do_sample === true || r.do_sample === "true");
        setUseCache(r.use_cache === true || r.use_cache === "true");
        setPerformConversationSummary(
          r.perform_conversation_summary === true || r.perform_conversation_summary === "true",
        );
        setSummarizeAfterNTurns(Number(r.summarize_after_n_turns ?? 8));
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

  // Apply preset on first load
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

  const setOverride = useCallback((key: string, value: number | boolean) => {
    setters[key](value);
    if (activePresetRef.current) {
      const all = loadOverrides();
      const label = activePresetRef.current;
      const preset = presets.find((p) => p.label === label);
      const presetDefault = preset?.args?.[key];
      const labelOverrides = { ...(all[label] ?? {}) };
      if (presetDefault !== undefined && presetDefault === value) {
        delete labelOverrides[key];
      } else {
        labelOverrides[key] = value;
      }
      if (Object.keys(labelOverrides).length === 0) delete all[label];
      else all[label] = labelOverrides;
      saveOverrides(all);
      setOverriddenLabels(computeOverriddenLabels(all));
      setSelectKey((n) => n + 1);
    }
    persist({ [key]: value });
  }, [persist, presets]);

  const handlePresetChange = useCallback((label: string) => {
    persistOverrides();
    setSelectedPreset(label);
    activePresetRef.current = label;
    const preset = presets.find((p) => p.label === label);
    if (!preset) return;
    const merged = { ...preset.args, ...overridesForLabel(label) };
    applyValues(merged);
    persist(merged);
  }, [presets, persistOverrides, applyValues, persist]);

  const resetToDefaults = useCallback(() => {
    const label = activePresetRef.current;
    if (!label) return;
    const all = loadOverrides();
    delete all[label];
    saveOverrides(all);
    setOverriddenLabels((prev) => { const next = new Set(prev); next.delete(label); return next; });
    setSelectKey((n) => n + 1);
    const preset = presets.find((p) => p.label === label);
    if (preset) { applyValues(preset.args); persist(preset.args); }
  }, [presets, applyValues, persist]);

  const resetAllToDefaults = useCallback(() => {
    saveOverrides({});
    setOverriddenLabels(new Set());
    setSelectKey((n) => n + 1);
    if (selectedPreset) {
      const preset = presets.find((p) => p.label === selectedPreset);
      if (preset) { applyValues(preset.args); persist(preset.args); }
    }
  }, [presets, selectedPreset, applyValues, persist]);

  const handlePrecisionChange = useCallback((value: string) => {
    setPrecision(value);
    persist({ dtype: value });
  }, [persist]);

  return {
    loading, precision, precisionOptions,
    presets, selectedPreset, overrideEnabled, overriddenLabels, selectKey,
    performConversationSummary, summarizeAfterNTurns,
    collectValues, activePresetRef,
    setOverrideEnabled, setOverride, handlePresetChange,
    resetToDefaults, resetAllToDefaults, handlePrecisionChange,
    setPerformConversationSummary: (v: boolean) => { setPerformConversationSummary(v); persist({ perform_conversation_summary: v }); },
    setSummarizeAfterNTurns: (v: number) => { setSummarizeAfterNTurns(v); persist({ summarize_after_n_turns: v }); },
  };
}
