import { useState, useCallback, useRef, useEffect } from "react";
import { getHardwareProfile, unloadModel, loadModel, getSingleton } from "../../../api/client";
import type { HardwareProfile, ActiveModelInfo } from "../../../api/client";

export interface ModelSlot {
  type: string;
  label: string;
  name: string;
  canLoad: boolean;
}

export function useStatsPanel() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);
  const [models, setModels] = useState<ActiveModelInfo[]>([]);
  const [slots, setSlots] = useState<ModelSlot[]>([]);
  const [unloadingSlots, setUnloadingSlots] = useState<Set<string>>(new Set());
  const mountedRef = useRef(true);
  const loadingRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    (async () => {
      try {
        const [llmRec, artRec, pathRec, espeakRec, openvoiceRec] = await Promise.all([
          getSingleton("LLMGeneratorSettings").catch(() => null),
          getSingleton("GeneratorSettings").catch(() => null),
          getSingleton("PathSettings").catch(() => null),
          getSingleton("EspeakSettings").catch(() => null),
          getSingleton("OpenVoiceSettings").catch(() => null),
        ]);

        const llmName = String(llmRec?.model_path ?? "");

        const artVersion = String(artRec?.version ?? "");
        const artModel = String(artRec?.custom_path ?? "");
        const artRawName = artModel.split("/").pop() || artModel.split("\\").pop() || artModel;
        const artName = artVersion + (artRawName.replace(/\.[^.]+$/, "") ? `/${artRawName.replace(/\.[^.]+$/, "")}` : "");

        const sttRaw = String(pathRec?.stt_model_path ?? "");
        const sttBase = sttRaw.split("/").pop() || sttRaw.split("\\").pop() || "";
        const sttName = sttBase && sttBase !== "stt" ? sttBase : "whisper";

        const ovVoice = String(openvoiceRec?.voice ?? "");
        const ovRef = String(openvoiceRec?.reference_speaker_path ?? "");
        const espeakVoice = String(espeakRec?.voice ?? "english (america)");
        const useOpenVoice = !!(ovVoice !== "default" || (ovRef && ovRef !== "default"));
        const ttsName = useOpenVoice
          ? `openvoice${ovRef && ovRef !== "default" ? ` - ${ovRef}` : ""}`
          : `espeak - ${espeakVoice}`;

        setSlots([
          { type: "llm", label: "LLM", name: llmName, canLoad: !!llmName },
          { type: "art", label: "Art", name: artName || "none", canLoad: !!artModel },
          { type: "stt", label: "STT", name: sttName || "none", canLoad: !!sttName },
          { type: "tts", label: "TTS", name: ttsName, canLoad: useOpenVoice },
          { type: "embedding", label: "Embedding", name: "e5-large", canLoad: true },
          { type: "rmbg", label: "RMBG", name: "RMBG-2.0", canLoad: false },
        ]);
      } catch {
        setSlots([
          { type: "llm", label: "LLM", name: "", canLoad: false },
          { type: "art", label: "Art", name: "", canLoad: false },
          { type: "stt", label: "STT", name: "", canLoad: false },
          { type: "tts", label: "TTS", name: "", canLoad: false },
          { type: "embedding", label: "Embedding", name: "e5-large", canLoad: true },
          { type: "rmbg", label: "RMBG", name: "RMBG-2.0", canLoad: false },
        ]);
      }
    })();
  }, []);

  const fetchActiveModels = useCallback(async () => {
    try {
      const { listActiveModels } = await import("../../../api/client");
      const resp = await listActiveModels();
      setModels(resp.models ?? []);
    } catch { /* endpoint may be unavailable */ }
  }, []);

  const fetchHw = useCallback(async () => {
    try {
      const data = await getHardwareProfile();
      if (mountedRef.current) { setHw(data); fetchActiveModels(); }
    } catch { /* endpoint may be unavailable */ }
  }, [fetchActiveModels]);

  useEffect(() => {
    mountedRef.current = true;
    fetchHw();
    const id = setInterval(fetchHw, 100);
    return () => { mountedRef.current = false; clearInterval(id); };
  }, [fetchHw]);

  const handleUnload = useCallback((m: ActiveModelInfo, slotType: string) => {
    if (unloadingSlots.has(slotType)) return;
    // Optimistically flip the slot to "unloading" so the indicator is
    // instant on click rather than waiting for the server round-trip.
    setUnloadingSlots((prev) => new Set(prev).add(slotType));
    loadingRef.current.delete(slotType);
    unloadModel(m.model_id, m.model_type).catch(() => {});
    // Safety net: clear the optimistic flag if the unload never completes.
    setTimeout(() => {
      setUnloadingSlots((prev) => {
        if (!prev.has(slotType)) return prev;
        const next = new Set(prev);
        next.delete(slotType);
        return next;
      });
    }, 15000);
  }, [unloadingSlots]);

  const handleLoad = useCallback((type: string, id: string) => {
    loadingRef.current.add(type);
    loadModel(id, type).catch(() => {});
  }, []);

  const findModelIn = useCallback(
    (list: ActiveModelInfo[], type: string): ActiveModelInfo | undefined => {
      const prefixes = type === "art" ? [type, "text_to_image"] : [type];
      return list.find((m) =>
        prefixes.some((prefix) =>
          m.model_type.toLowerCase().startsWith(prefix),
        ),
      );
    },
    [],
  );

  // Clear the optimistic "unloading" flag once the server reports the model
  // gone (removed from the active list) or unloaded.
  useEffect(() => {
    setUnloadingSlots((prev) => {
      if (prev.size === 0) return prev;
      const next = new Set(prev);
      for (const type of prev) {
        const m = findModelIn(models, type);
        if (!m || m.status === "unloaded") next.delete(type);
      }
      return next.size === prev.size ? prev : next;
    });
  }, [models, findModelIn]);

  const findModel = useCallback(
    (type: string): ActiveModelInfo | undefined => {
      // The art/SD model is registered with model_type "text_to_image"
      // in BaseDiffusersModelManager, so match both "art" and
      // "text_to_image" when looking up the "art" slot.
      const prefixes = type === "art"
        ? [type, "text_to_image"]
        : [type];
      return models.find((m) =>
        prefixes.some((prefix) =>
          m.model_type.toLowerCase().startsWith(prefix),
        ),
      );
    },
    [models],
  );

  const statusColor = (status: string) => {
    switch (status) {
      case "loaded": return "var(--bs-success)";
      case "loading":
      case "unloading": return "var(--bs-warning)";
      default: return "var(--bs-danger)";
    }
  };

  return { hw, slots, models, loadingRef, unloadingSlots, findModel, statusColor, handleLoad, handleUnload };
}
