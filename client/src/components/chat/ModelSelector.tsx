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

export default function ModelSelector() {
  const [modelPath, setModelPath] = useState("");
  const [modelService, setModelService] = useState("local");
  const [localModels, setLocalModels] = useState<
    { label: string; value: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const isLocal = modelService === "local";

  const fetchSettings = useCallback(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r: ResourceRecord) => {
        setModelPath(String(r.model_path ?? ""));
        setModelService(String(r.model_service ?? "local"));
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

  // Reload models when file-system changes are detected (via event bus)
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
    <div className="d-flex gap-2 align-items-center">
      <Form.Select
        size="sm"
        value={modelService}
        onChange={(e) => {
          setModelService(e.target.value);
          persist({ model_service: e.target.value });
        }}
        style={{ width: "auto", minWidth: 130 }}
      >
        <option value="local">Local</option>
        <option value="openrouter">OpenRouter (API)</option>
        <option value="ollama">Ollama</option>
      </Form.Select>

      {isLocal ? (
        <Form.Select
          size="sm"
          className="flex-grow-1"
          value={modelPath}
          onChange={(e) => {
            setModelPath(e.target.value);
            persist({ model_path: e.target.value });
          }}
          style={{ width: "auto", minWidth: 180 }}
        >
          <option value="">Select model...</option>
          {localModels.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </Form.Select>
      ) : (
        <Form.Control
          size="sm"
          className="flex-grow-1"
          value={modelPath}
          onChange={(e) => {
            setModelPath(e.target.value);
            persist({ model_path: e.target.value });
          }}
          placeholder="model-id or endpoint URL"
          style={{ width: "auto", minWidth: 180 }}
        />
      )}
    </div>
  );
}
