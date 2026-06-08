import { useState, useEffect, useCallback } from "react";
import {
  getSingleton,
  updateSingleton,
  listLLMModels,
} from "../../api/client";
import type { ResourceRecord } from "../../types/api";
import Form from "react-bootstrap/Form";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_MODEL_STATUS } from "../../features/events/types";

const MODEL_CHANGED_EVENT = "model-settings-changed";

const PROVIDER_LABELS: Record<string, string> = {
  local: "Local",
  openrouter: "OpenRouter",
  ollama: "Ollama",
  openai: "OpenAI",
};

const PROVIDER_COLORS: Record<string, string> = {
  local: "var(--bs-success)",
  openrouter: "var(--bs-info)",
  ollama: "var(--bs-warning)",
  openai: "var(--bs-primary)",
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
  const needsApiKey = modelService === "openrouter" || modelService === "openai";

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

  useEventBus([EVENT_MODEL_STATUS], () => { fetchSettings(); });

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("LLMGeneratorSettings", updates)
      .then(() => {
        window.dispatchEvent(new CustomEvent(MODEL_CHANGED_EVENT));
      })
      .catch(() => {});
  };

  if (loading) {
    return null;
  }

  return (
    <div className="d-flex flex-column gap-1" style={{ minWidth: 0 }}>
      <div className="d-flex gap-2 align-items-center" style={{ minWidth: 0 }}>
        <div className="d-flex align-items-center gap-1" style={{ flexShrink: 0 }}>
          <span
            style={{
              display: "inline-block",
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: PROVIDER_COLORS[modelService] ?? "var(--bs-secondary)",
              flexShrink: 0,
            }}
            title={`Active backend: ${PROVIDER_LABELS[modelService] ?? modelService}`}
          />
          <Form.Select
            size="sm"
            value={modelService}
            onChange={(e) => {
              setModelService(e.target.value);
              persist({ model_service: e.target.value });
            }}
            style={{ width: "auto" }}
          >
            <option value="local">Local</option>
            <option value="openrouter">OpenRouter (API)</option>
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI</option>
          </Form.Select>
        </div>

        {isLocal ? (
          <Form.Select
            size="sm"
            value={modelPath}
            onChange={(e) => {
              setModelPath(e.target.value);
              persist({ model_path: e.target.value });
            }}
            style={{ flex: "1 1 0%", minWidth: 0 }}
          >
            <option value="">Select model...</option>
            {localModels.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </Form.Select>
        ) : (
          <Form.Control
            size="sm"
            value={modelPath}
            onChange={(e) => {
              setModelPath(e.target.value);
              persist({ model_path: e.target.value });
            }}
            placeholder={isOllama ? "Model name (e.g. llama3)" : "Model ID"}
            style={{ flex: "1 1 0%", minWidth: 0 }}
          />
        )}
      </div>

      {isOllama && (
        <Form.Control
          size="sm"
          value={apiBaseUrl}
          onChange={(e) => {
            setApiBaseUrl(e.target.value);
            persist({ api_base_url: e.target.value });
          }}
          placeholder="Ollama base URL (default: http://localhost:11434)"
          style={{ fontSize: "0.75rem" }}
        />
      )}

      {needsApiKey && (
        <Form.Control
          size="sm"
          type="password"
          value={apiKey}
          onChange={(e) => {
            setApiKey(e.target.value);
            persist({ api_key: e.target.value });
          }}
          placeholder={`${PROVIDER_LABELS[modelService] ?? modelService} API key`}
          style={{ fontSize: "0.75rem" }}
        />
      )}
    </div>
  );
}
