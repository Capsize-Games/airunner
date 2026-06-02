import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getPrivacySettings,
  updatePrivacySettings,
  getSingleton,
  updateSingleton,
} from "../../../api/client";

export default function HuggingFaceSection() {
  const [apiKey, setApiKey] = useState("");
  const [allowHf, setAllowHf] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [privacy, appSettings] = await Promise.all([
          getPrivacySettings(),
          getSingleton("ApplicationSettings").catch(() => ({})),
        ]);
        if (cancelled) return;
        setAllowHf(privacy.services?.huggingface !== false);
        setApiKey(String(appSettings.hf_api_key_read_key ?? ""));
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function handleToggle(checked: boolean) {
    setAllowHf(checked);
    updatePrivacySettings({ huggingface: checked }).catch(() => {});
  }

  async function saveApiKey() {
    await updateSingleton("ApplicationSettings", {
      hf_api_key_read_key: apiKey || null,
    } as Record<string, unknown>).catch(() => {});
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
      <h6 className="mb-3">HuggingFace</h6>

      <Form.Group className="mb-2">
        <Form.Check
          type="switch"
          label="Allow HuggingFace downloads"
          checked={allowHf}
          onChange={(e) => handleToggle(e.target.checked)}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-3">
        <Form.Label className="small">API Read Key</Form.Label>
        <Form.Control
          type="password"
          size="sm"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          onBlur={saveApiKey}
          className="bg-dark text-light border-secondary"
          placeholder="Enter HuggingFace read key"
        />
      </Form.Group>
    </div>
  );
}
