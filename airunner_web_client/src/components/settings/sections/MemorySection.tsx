import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
  getHardwareProfile,
  getArtModelOptions,
} from "../../../api/client";

interface MemorySettings {
  use_accelerated_transformers: boolean;
  use_attention_slicing: boolean;
  use_enable_sequential_cpu_offload: boolean;
  enable_model_cpu_offload: boolean;
  use_last_channels: boolean;
  use_tf32: boolean;
  use_enable_vae_slicing: boolean;
  use_tiled_vae: boolean;
  use_tome_sd: boolean;
  tome_sd_ratio: number;
  default_gpu_sd: string;
  default_gpu_llm: string;
  default_gpu_tts: string;
  default_gpu_stt: string;
  prevent_unload_on_llm_image_generation: boolean;
}

const DEFAULTS: MemorySettings = {
  use_accelerated_transformers: true,
  use_attention_slicing: false,
  use_enable_sequential_cpu_offload: false,
  enable_model_cpu_offload: false,
  use_last_channels: true,
  use_tf32: false,
  use_enable_vae_slicing: true,
  use_tiled_vae: true,
  use_tome_sd: true,
  tome_sd_ratio: 0.6,
  default_gpu_sd: "0",
  default_gpu_llm: "0",
  default_gpu_tts: "0",
  default_gpu_stt: "0",
  prevent_unload_on_llm_image_generation: false,
};

export default function MemorySection() {
  const [settings, setSettings] = useState<MemorySettings>(DEFAULTS);
  const [numGpus, setNumGpus] = useState(0);
  const [precisions, setPrecisions] = useState<
    { label: string; value: string }[]
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [mem, hardware, opts] = await Promise.all([
          getSingleton("MemorySettings"),
          getHardwareProfile().catch(() => ({ num_gpus: 0 })),
          getArtModelOptions().catch(() => ({ precisions: [] })),
        ]);
        if (cancelled) return;
        setNumGpus(Number(hardware.num_gpus ?? 0));
        setSettings({
          use_accelerated_transformers:
            mem.use_accelerated_transformers !== false,
          use_attention_slicing:
            mem.use_attention_slicing === true,
          use_enable_sequential_cpu_offload:
            mem.use_enable_sequential_cpu_offload === true,
          enable_model_cpu_offload:
            mem.enable_model_cpu_offload === true,
          use_last_channels:
            mem.use_last_channels !== false,
          use_tf32:
            mem.use_tf32 === true,
          use_enable_vae_slicing:
            mem.use_enable_vae_slicing !== false,
          use_tiled_vae:
            mem.use_tiled_vae !== false,
          use_tome_sd:
            mem.use_tome_sd !== false,
          tome_sd_ratio:
            Number(mem.tome_sd_ratio ?? 0.6),
          default_gpu_sd:
            String(mem.default_gpu_sd ?? "0"),
          default_gpu_llm:
            String(mem.default_gpu_llm ?? "0"),
          default_gpu_tts:
            String(mem.default_gpu_tts ?? "0"),
          default_gpu_stt:
            String(mem.default_gpu_stt ?? "0"),
          prevent_unload_on_llm_image_generation:
            mem.prevent_unload_on_llm_image_generation === true,
        });
        setPrecisions(opts.precisions ?? []);
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function setField<K extends keyof MemorySettings>(
    key: K,
    value: MemorySettings[K],
  ) {
    const next = { ...settings, [key]: value };
    setSettings(next);
    updateSingleton(
      "MemorySettings",
      next as unknown as Record<string, unknown>,
    ).catch(() => {});
  }

  function resetToDefaults() {
    setSettings(DEFAULTS);
    updateSingleton(
      "MemorySettings",
      DEFAULTS as unknown as Record<string, unknown>,
    ).catch(() => {});
  }

  const gpuOptions = Array.from(
    { length: Math.max(numGpus, 1) },
    (_, i) => ({ label: `GPU ${i}`, value: String(i) }),
  );

  if (loading) {
    return (
      <div className="text-center py-4">
        <Spinner animation="border" size="sm" />
      </div>
    );
  }

  return (
    <div>
      <h6 className="mb-3">Memory Settings</h6>

      {numGpus > 1 && (
        <div className="mb-3">
          <h6 className="small text-muted mb-2">
            Model Assignment
          </h6>
          {([
            { key: "default_gpu_sd" as const,
              label: "SD Model GPU" },
            { key: "default_gpu_llm" as const,
              label: "LLM Model GPU" },
            { key: "default_gpu_tts" as const,
              label: "TTS Model GPU" },
            { key: "default_gpu_stt" as const,
              label: "STT Model GPU" },
          ]).map(({ key, label }) => (
            <Form.Group key={key} className="mb-2">
              <Form.Label className="small">{label}</Form.Label>
              <Form.Select
                size="sm"
                value={settings[key]}
                onChange={(e) => setField(key, e.target.value)}
                className="bg-dark text-light border-secondary"
              >
                {gpuOptions.map((gpu) => (
                  <option key={gpu.value} value={gpu.value}>
                    {gpu.label}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          ))}
          <Form.Group className="mb-2">
            <Form.Check
              type="switch"
              label={
                "Disable auto model management " +
                "on LLM image generation"
              }
              checked={
                settings.prevent_unload_on_llm_image_generation
              }
              onChange={(e) =>
                setField(
                  "prevent_unload_on_llm_image_generation",
                  e.target.checked,
                )
              }
              className="small"
            />
          </Form.Group>
        </div>
      )}

      <div className="mb-3">
        <h6 className="small text-muted mb-2">
          Memory Optimization
        </h6>
        {([
          { key: "use_accelerated_transformers" as const,
            label: "Accelerated Transformers" },
          { key: "use_attention_slicing" as const,
            label: "Attention Slicing" },
          { key: "use_enable_sequential_cpu_offload" as const,
            label: "Sequential CPU offload" },
          { key: "enable_model_cpu_offload" as const,
            label: "Model CPU offload" },
          { key: "use_last_channels" as const,
            label: "Channels last memory format" },
          { key: "use_tf32" as const,
            label: "TF32 precision" },
          { key: "use_enable_vae_slicing" as const,
            label: "VAE Slicing" },
          { key: "use_tiled_vae" as const,
            label: "Tile VAE" },
        ]).map(({ key, label }) => (
          <Form.Group key={key} className="mb-1">
            <Form.Check
              type="switch"
              label={label}
              checked={settings[key]}
              onChange={(e) =>
                setField(key, e.target.checked)
              }
              className="small"
            />
          </Form.Group>
        ))}
      </div>

      <div className="mb-3">
        <h6 className="small text-muted mb-2">
          ToMe Token Merging
        </h6>
        <Form.Group className="mb-2">
          <Form.Check
            type="switch"
            label="Enable ToMe SD"
            checked={settings.use_tome_sd}
            onChange={(e) =>
              setField("use_tome_sd", e.target.checked)
            }
            className="small"
          />
        </Form.Group>
        {settings.use_tome_sd && (
          <Form.Group className="mb-2">
            <Form.Label className="small">
              ToMe ratio:{" "}
              {settings.tome_sd_ratio.toFixed(2)}
            </Form.Label>
            <Form.Range
              min={0}
              max={1}
              step={0.01}
              value={settings.tome_sd_ratio}
              onChange={(e) =>
                setField(
                  "tome_sd_ratio",
                  Number(e.target.value),
                )
              }
            />
          </Form.Group>
        )}
      </div>

      <div className="d-flex gap-2 mb-3">
        <button
          className="btn btn-sm"
          style={{
            background: "var(--bs-primary)",
            border: "none",
            color: "#fff",
          }}
          onClick={resetToDefaults}
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  );
}
