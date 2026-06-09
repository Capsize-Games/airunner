import { useState, useEffect, useCallback } from "react";
import {
  getSingleton,
  updateSingleton,
  listLLMModels,
  listActiveModels,
} from "../../api/client";
import type { ResourceRecord } from "../../types/api";
import type { ActiveModelInfo } from "../../api/client";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_MODEL_STATUS } from "../../features/events/types";
import { ProviderPicker } from "./ProviderPicker";
import { ModelPicker } from "./ModelPicker";

const MODEL_CHANGED_EVENT = "model-settings-changed";

const PROVIDER_COLORS: Record<string, string> = {
  local: "var(--bs-success)",
  openrouter: "var(--bs-info)",
  ollama: "var(--bs-warning)",
  openai: "var(--bs-primary)",
};

const PROVIDER_LABELS: Record<string, string> = {
  local: "Local",
  openrouter: "OpenRouter",
  ollama: "Ollama",
  openai: "OpenAI",
};

export default function ModelSelector() {
  const [modelPath, setModelPath] = useState("");
  const [modelService, setModelService] = useState("local");
  const [apiKey, setApiKey] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [localModels, setLocalModels] = useState<
    { label: string; value: string }[]
  >([]);
  const [loading, setLoading] = useState(true);

  const isLocal = modelService === "local";
  const isOllama = modelService === "ollama";

  const fetchSettings = useCallback(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r: ResourceRecord) => {
        setModelPath(String(r.model_path ?? ""));
        setModelService(String(r.model_service ?? "local"));
        setApiKey(String(r.api_key ?? ""));
        setApiBaseUrl(String(r.api_base_url ?? ""));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    listLLMModels()
      .then((models) => setLocalModels(models))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchSettings();
    const handler = () => fetchSettings();
    window.addEventListener(MODEL_CHANGED_EVENT, handler);
    return () => window.removeEventListener(MODEL_CHANGED_EVENT, handler);
  }, [fetchSettings]);

  const [modelStatus, setModelStatus] = useState<string>("unloaded");

  const fetchModelStatus = useCallback(async () => {
    try {
      const resp = await listActiveModels();
      const llm = resp.models.find(
        (m: ActiveModelInfo) => m.model_type.toLowerCase() === "llm",
      );
      setModelStatus(llm?.status ?? "unloaded");
    } catch {
      // endpoint may be unavailable
    }
  }, []);

  useEffect(() => {
    fetchModelStatus();
    const id = setInterval(fetchModelStatus, 300);
    return () => clearInterval(id);
  }, [fetchModelStatus]);

  useEventBus([EVENT_MODEL_STATUS], () => {
    fetchSettings();
    fetchModelStatus();
  });

  const statusDotColor = isLocal
    ? modelStatus === "loaded"
      ? "var(--bs-success)"
      : modelStatus === "loading"
        ? "var(--bs-warning)"
        : "var(--bs-danger)"
    : PROVIDER_COLORS[modelService] ?? "var(--bs-secondary)";

  const statusDotTitle = isLocal
    ? `LLM: ${modelStatus}`
    : `Active backend: ${PROVIDER_LABELS[modelService] ?? modelService}`;

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("LLMGeneratorSettings", updates)
      .then(() => {
        window.dispatchEvent(new CustomEvent(MODEL_CHANGED_EVENT));
      })
      .catch(() => {});
  };

  if (loading) return null;

  return (
    <div
      className="d-flex align-items-center min-w-0"
      style={{ flex: "1 1 0%", gap: 0 }}
    >
      <ProviderPicker
        value={modelService}
        apiKey={apiKey}
        apiBaseUrl={apiBaseUrl}
        statusDotColor={statusDotColor}
        statusDotTitle={statusDotTitle}
        onChangeProvider={(v) => {
          setModelService(v);
          persist({ model_service: v });
        }}
        onChangeApiKey={(v) => {
          setApiKey(v);
          persist({ api_key: v });
        }}
        onChangeApiBaseUrl={(v) => {
          setApiBaseUrl(v);
          persist({ api_base_url: v });
        }}
      />

      <span
        style={{
          width: 1,
          height: 14,
          background: "rgba(255,255,255,0.15)",
          flexShrink: 0,
        }}
      />

      <ModelPicker
        value={modelPath}
        isLocal={isLocal}
        isOllama={isOllama}
        localModels={localModels}
        onChangeModel={(v) => {
          setModelPath(v);
          persist({ model_path: v });
        }}
      />
    </div>
  );
}
