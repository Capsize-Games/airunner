import { useState, useEffect, useCallback, useRef } from "react";
import ProgressBar from "react-bootstrap/ProgressBar";
import {
  getHardwareProfile,
  unloadModel,
  loadModel,
  getSingleton,
} from "../../api/client";
import type { HardwareProfile } from "../../types/api";
import type { ActiveModelInfo } from "../../api/client";
import LucideIcon from "../shared/LucideIcon";

interface ModelSlot {
  type: string;
  label: string;
  name: string;
  /** If true, the load/play button is shown. */
  canLoad: boolean;
}

const MODEL_SLOTS: { type: string; label: string }[] = [
  { type: "llm", label: "LLM" },
  { type: "art", label: "Art" },
  { type: "stt", label: "STT" },
  { type: "tts", label: "TTS" },
];

export default function StatsPanel() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);
  const [models, setModels] = useState<ActiveModelInfo[]>([]);
  const [slots, setSlots] = useState<ModelSlot[]>([]);
  const mountedRef = useRef(true);
  const unloadingRef = useRef<Set<string>>(new Set());

  // Fetch configured model names from settings once on mount.
  useEffect(() => {
    (async () => {
      try {
        const [llmRec, artRec, pathRec, espeakRec, openvoiceRec] =
          await Promise.all([
            getSingleton("LLMGeneratorSettings").catch(() => null),
            getSingleton("GeneratorSettings").catch(() => null),
            getSingleton("PathSettings").catch(() => null),
            getSingleton("EspeakSettings").catch(() => null),
            getSingleton("OpenVoiceSettings").catch(() => null),
          ]);

        // ── LLM ──────────────────────────────────────────────────────
        const llmName = String(llmRec?.model_path ?? "");

        // ── Art ──────────────────────────────────────────────────────
        const artVersion = String(artRec?.version ?? "");
        const artModel = String(artRec?.custom_path ?? "");
        const artRawName = artModel.split("/").pop() || artModel.split("\\").pop() || artModel;
        const artModelName = artRawName.replace(/\.[^.]+$/, "");
        const artName = artVersion + (artModelName ? `/${artModelName}` : "");

        // ── STT ──────────────────────────────────────────────────────
        const sttRaw = String(pathRec?.stt_model_path ?? "");
        const sttBase = sttRaw.split("/").pop() || sttRaw.split("\\").pop() || "";
        const sttName = sttBase && sttBase !== "stt" ? sttBase : "whisper";

        // ── TTS ──────────────────────────────────────────────────────
        // If OpenVoice has a non-default voice, show it; else espeak.
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
          {
            type: "tts",
            label: "TTS",
            name: ttsName,
            canLoad: useOpenVoice,
          },
        ]);
      } catch {
        setSlots(MODEL_SLOTS.map((s) => ({ ...s, name: "", canLoad: false })));
      }
    })();
  }, []);

  const fetchActiveModels = useCallback(async () => {
    try {
      const { listActiveModels } = await import("../../api/client");
      const resp = await listActiveModels();
      setModels(resp.models ?? []);
    } catch {
      // endpoint may be unavailable
    }
  }, []);

  const fetchHw = useCallback(async () => {
    try {
      const data = await getHardwareProfile();
      if (mountedRef.current) {
        setHw(data);
        fetchActiveModels();
      }
    } catch {
      // endpoint may be unavailable
    }
  }, [fetchActiveModels]);

  useEffect(() => {
    mountedRef.current = true;
    fetchHw();
    const id = setInterval(fetchHw, 100);
    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
  }, [fetchHw]);

  const handleUnload = (m: ActiveModelInfo) => {
    const key = m.model_id || m.model_type;
    if (unloadingRef.current.has(key)) return;
    unloadingRef.current.add(key);
    unloadModel(m.model_id, m.model_type).catch(() => {});
    setTimeout(() => unloadingRef.current.delete(key), 2000);
  };

  const handleLoad = (type: string, id: string) => {
    loadModel(id, type).catch(() => {});
  };

  const findModel = (type: string): ActiveModelInfo | undefined =>
    models.find((m) => m.model_type.toLowerCase().startsWith(type));

  const statusColor = (status: string) => {
    switch (status) {
      case "loaded": return "var(--bs-success)";
      case "loading": return "var(--bs-warning)";
      default: return "var(--bs-danger)";
    }
  };

  if (!hw) {
    return (
      <div className="p-2">
        <h6 className="text-muted mb-2">Model Resources</h6>
        <p className="text-muted small">
          Hardware info unavailable.
        </p>
      </div>
    );
  }

  const vramUsed =
    hw.total_vram_gb > 0
      ? hw.total_vram_gb - hw.available_vram_gb
      : 0;
  const vramPct =
    hw.total_vram_gb > 0
      ? (vramUsed / hw.total_vram_gb) * 100
      : 0;
  const ramUsed =
    hw.total_ram_gb > 0
      ? hw.total_ram_gb - hw.available_ram_gb
      : 0;
  const ramPct =
    hw.total_ram_gb > 0
      ? (ramUsed / hw.total_ram_gb) * 100
      : 0;

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Model Resources</h6>

      <div className="small text-muted mb-2">
        {hw.device_name ?? "CPU"} &middot; {hw.cpu_count}{" "}
        cores &middot; {hw.num_gpus} GPU(s)
      </div>

      {/* VRAM bar */}
      <div className="mb-2">
        <small className="text-muted">VRAM</small>
        <ProgressBar
          now={Math.min(vramPct, 100)}
          variant={vramPct > 90 ? "danger" : "success"}
          className="mt-1"
          style={{ height: 8 }}
        />
        <small className="text-muted">
          {vramUsed.toFixed(1)} /{" "}
          {hw.total_vram_gb.toFixed(1)} GB
        </small>
      </div>

      {/* RAM bar */}
      <div className="mb-2">
        <small className="text-muted">RAM</small>
        <ProgressBar
          now={Math.min(ramPct, 100)}
          variant={ramPct > 90 ? "danger" : "info"}
          className="mt-1"
          style={{ height: 8 }}
        />
        <small className="text-muted">
          {ramUsed.toFixed(1)} /{" "}
          {hw.total_ram_gb.toFixed(1)} GB
        </small>
      </div>

      {/* Models list */}
      <div className="mt-2">
        <small className="text-muted d-block mb-1">
          Models
        </small>
        {slots.map(({ type, label, name, canLoad }) => {
          const m = findModel(type);
          const status = m?.status ?? "unloaded";
          return (
            <div
              key={type}
              className="d-flex align-items-center justify-content-between mb-1"
              style={{ fontSize: "11px" }}
            >
              <span className="text-truncate" style={{ maxWidth: "70%" }}>
                <span
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    backgroundColor: statusColor(status),
                    marginRight: 4,
                    flexShrink: 0,
                  }}
                />
                {label}: {name || "none"}
              </span>
              {m?.can_unload ? (
                <button
                  onClick={() => handleUnload(m)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#aaa",
                    cursor: "pointer",
                    padding: 0,
                    display: "flex",
                    alignItems: "center",
                    flexShrink: 0,
                  }}
                  title={`Unload ${label}`}
                >
                  <LucideIcon name="octagon-alert" size={14} />
                </button>
              ) : canLoad ? (
                <button
                  onClick={() => handleLoad(type, name)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#aaa",
                    cursor: "pointer",
                    padding: 0,
                    display: "flex",
                    alignItems: "center",
                    flexShrink: 0,
                  }}
                  title={`Load ${label}`}
                >
                  <LucideIcon name="play" size={14} />
                </button>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
