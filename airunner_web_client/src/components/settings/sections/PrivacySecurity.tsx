import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  getPrivacySettings,
  updatePrivacySettings,
  getSingleton,
  updateSingleton,
} from "../../../api/client";
import type { ResourceRecord } from "../../../types/api";

const SERVICE_KEYS = [
  { key: "huggingface", label: "Allow HuggingFace downloads" },
  { key: "civitai", label: "Allow CivitAI downloads" },
  { key: "duckduckgo", label: "Allow DuckDuckGo web search" },
  { key: "openmeteo", label: "Allow Open-Meteo weather API" },
  { key: "openrouter", label: "Allow OpenRouter API" },
  { key: "openai", label: "Allow OpenAI API" },
];

export default function PrivacySecuritySection() {
  const [services, setServices] = useState<Record<string, boolean>>({});
  const [hfReadKey, setHfReadKey] = useState("");
  const [hfWriteKey, setHfWriteKey] = useState("");
  const [civitAiKey, setCivitAiKey] = useState("");
  const [openRouterKey, setOpenRouterKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [privacy, appSettings] = await Promise.all([
          getPrivacySettings(),
          getSingleton("ApplicationSettings"),
        ]);
        if (cancelled) return;
        setServices(privacy.services ?? {});
        setHfReadKey(String(appSettings.hf_api_key_read_key ?? ""));
        setHfWriteKey(String(appSettings.hf_api_key_write_key ?? ""));
        setCivitAiKey(String(appSettings.civit_ai_api_key ?? ""));
        setOpenRouterKey(String(appSettings.openrouter_api_key ?? ""));
      } catch {
        // silently fail
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await Promise.all([
        updatePrivacySettings(services),
        updateSingleton("ApplicationSettings", {
          hf_api_key_read_key: hfReadKey || null,
          hf_api_key_write_key: hfWriteKey || null,
          civit_ai_api_key: civitAiKey || null,
          openrouter_api_key: openRouterKey || null,
        } as Record<string, unknown>),
      ]);
    } finally {
      setSaving(false);
    }
  }

  function toggleAll(enabled: boolean) {
    const next: Record<string, boolean> = {};
    for (const { key } of SERVICE_KEYS) {
      next[key] = enabled;
    }
    setServices(next);
  }

  if (loading) {
    return (
      <div className="text-center py-4">
        <Spinner animation="border" size="sm" />
      </div>
    );
  }

  return (
    <div>
      <h6 className="mb-3">Privacy & Security</h6>

      <div className="mb-3">
        <div className="d-flex gap-2 mb-2">
          <Button size="sm" variant="outline-success" onClick={() => toggleAll(true)}>
            Enable All
          </Button>
          <Button size="sm" variant="outline-danger" onClick={() => toggleAll(false)}>
            Disable All
          </Button>
        </div>
      </div>

      <div className="mb-3">
        <h6 className="small text-muted mb-2">Model Downloads</h6>
        {SERVICE_KEYS.filter((s) => s.key === "huggingface" || s.key === "civitai").map(({ key, label }) => (
          <Form.Group key={key} className="mb-1">
            <Form.Check
              type="switch"
              label={label}
              checked={!!services[key]}
              onChange={(e) =>
                setServices((prev) => ({ ...prev, [key]: e.target.checked }))
              }
              className="small"
            />
          </Form.Group>
        ))}
      </div>

      <div className="mb-3">
        <h6 className="small text-muted mb-2">Search & Research</h6>
        {SERVICE_KEYS.filter((s) => s.key === "duckduckgo").map(({ key, label }) => (
          <Form.Group key={key} className="mb-1">
            <Form.Check
              type="switch"
              label={label}
              checked={!!services[key]}
              onChange={(e) =>
                setServices((prev) => ({ ...prev, [key]: e.target.checked }))
              }
              className="small"
            />
          </Form.Group>
        ))}
      </div>

      <div className="mb-3">
        <h6 className="small text-muted mb-2">External LLM</h6>
        {SERVICE_KEYS.filter((s) => s.key === "openrouter" || s.key === "openai").map(({ key, label }) => (
          <Form.Group key={key} className="mb-1">
            <Form.Check
              type="switch"
              label={label}
              checked={!!services[key]}
              onChange={(e) =>
                setServices((prev) => ({ ...prev, [key]: e.target.checked }))
              }
              className="small"
            />
          </Form.Group>
        ))}
      </div>

      <div className="mb-3">
        <h6 className="small text-muted mb-2">Weather</h6>
        {SERVICE_KEYS.filter((s) => s.key === "openmeteo").map(({ key, label }) => (
          <Form.Group key={key} className="mb-1">
            <Form.Check
              type="switch"
              label={label}
              checked={!!services[key]}
              onChange={(e) =>
                setServices((prev) => ({ ...prev, [key]: e.target.checked }))
              }
              className="small"
            />
          </Form.Group>
        ))}
      </div>

      <div className="mb-3">
        <h6 className="small text-muted mb-2">API Keys</h6>
        <Form.Group className="mb-2">
          <Form.Label className="small">HuggingFace Read Key</Form.Label>
          <Form.Control
            type="password"
            size="sm"
            value={hfReadKey}
            onChange={(e) => setHfReadKey(e.target.value)}
            className="bg-dark text-light border-secondary"
            placeholder="Enter HF read key"
          />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label className="small">HuggingFace Write Key</Form.Label>
          <Form.Control
            type="password"
            size="sm"
            value={hfWriteKey}
            onChange={(e) => setHfWriteKey(e.target.value)}
            className="bg-dark text-light border-secondary"
            placeholder="Enter HF write key"
          />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label className="small">CivitAI API Key</Form.Label>
          <Form.Control
            type="password"
            size="sm"
            value={civitAiKey}
            onChange={(e) => setCivitAiKey(e.target.value)}
            className="bg-dark text-light border-secondary"
            placeholder="Enter CivitAI key"
          />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label className="small">OpenRouter API Key</Form.Label>
          <Form.Control
            type="password"
            size="sm"
            value={openRouterKey}
            onChange={(e) => setOpenRouterKey(e.target.value)}
            className="bg-dark text-light border-secondary"
            placeholder="Enter OpenRouter key"
          />
        </Form.Group>
      </div>

      <Button
        variant="primary"
        size="sm"
        onClick={handleSave}
        disabled={saving}
      >
        {saving ? <Spinner animation="border" size="sm" /> : "Save"}
      </Button>
    </div>
  );
}
