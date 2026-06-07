import { useState, useEffect, useCallback, useRef } from "react";
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
  const loadingRef = useRef<Set<string>>(new Set());

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

  const handleUnload = (m: ActiveModelInfo, slotType: string) => {
    const key = m.model_id || m.model_type;
    if (unloadingRef.current.has(key)) return;
    unloadingRef.current.add(key);
    loadingRef.current.delete(slotType);
    unloadModel(m.model_id, m.model_type).catch(() => {});
    setTimeout(() => unloadingRef.current.delete(key), 2000);
  };

  const handleLoad = (type: string, id: string) => {
    loadingRef.current.add(type);
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
      <div style={panelStyle}>
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
    <div style={panelStyle}>
      <h6 className="text-muted mb-2">Model Resources</h6>

      <div className="small text-muted mb-2">
        {hw.device_name ?? "CPU"} &middot; {hw.cpu_count}{" "}
        cores &middot; {hw.num_gpus} GPU(s)
      </div>

      {/* VRAM bar */}
      <div className="mb-2">
        <small className="text-muted">VRAM</small>
        <div style={progressOuter}>
          <div
            style={{
              ...progressInner,
              width: `${Math.min(vramPct, 100)}%`,
              backgroundColor:
                vramPct > 90
                  ? "var(--bs-danger)"
                  : "var(--bs-success)",
            }}
          />
        </div>
        <small className="text-muted">
          {vramUsed.toFixed(1)} /{" "}
          {hw.total_vram_gb.toFixed(1)} GB
        </small>
      </div>

      {/* RAM bar */}
      <div className="mb-2">
        <small className="text-muted">RAM</small>
        <div style={progressOuter}>
          <div
            style={{
              ...progressInner,
              width: `${Math.min(ramPct, 100)}%`,
              backgroundColor:
                ramPct > 90
                  ? "var(--bs-danger)"
                  : "var(--bs-info)",
            }}
          />
        </div>
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
              {status === "loading" || (status !== "loaded" && loadingRef.current.has(type)) ? (
                <span style={{ display: "flex", opacity: 0.5 }}>
                  <LucideIcon name="loader" size={14} />
                </span>
              ) : m?.can_unload ? (
                <button
                  className="model-action-btn"
                  onClick={() => handleUnload(m, type)}
                  title={`Unload ${label}`}
                >
                  <LucideIcon name="octagon-alert" size={14} />
                </button>
              ) : canLoad ? (
                <button
                  className="model-action-btn"
                  onClick={() => handleLoad(type, name)}
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

// ── Styles ────────────────────────────────────────────────────────────────────

const panelStyle: React.CSSProperties = {
  background: "#1a1a2e",
  border: "1px solid #444",
  borderRadius: 6,
  padding: "10px 12px",
  width: 280,
  fontFamily: "monospace",
  color: "#ccc",
  fontSize: 12,
  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
};

const progressOuter: React.CSSProperties = {
  width: "100%",
  height: 8,
  background: "#333",
  borderRadius: 4,
  marginTop: 4,
  overflow: "hidden",
};

const progressInner: React.CSSProperties = {
  height: "100%",
  borderRadius: 4,
  transition: "width 0.3s ease",
};
