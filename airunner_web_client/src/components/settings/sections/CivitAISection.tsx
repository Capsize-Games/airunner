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

export default function CivitAISection() {
  const [apiKey, setApiKey] = useState("");
  const [allowCivitai, setAllowCivitai] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [privacy, appSettings] = await Promise.all([
          getPrivacySettings(),
          getSingleton("ApplicationSettings").catch(() => ({})),
        ]);
        if (cancelled) return;
        setAllowCivitai(privacy.services?.civitai !== false);
        setApiKey(String(appSettings.civit_ai_api_key ?? ""));
      } catch {
        // ignore
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
        updatePrivacySettings({ civitai: allowCivitai }),
        updateSingleton("ApplicationSettings", {
          civit_ai_api_key: apiKey || null,
        } as Record<string, unknown>),
      ]);
    } finally {
      setSaving(false);
    }
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
      <h6 className="mb-3">CivitAI</h6>

      <Form.Group className="mb-2">
        <Form.Check
          type="switch"
          label="Allow CivitAI downloads"
          checked={allowCivitai}
          onChange={(e) => setAllowCivitai(e.target.checked)}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-3">
        <Form.Label className="small">API Key</Form.Label>
        <Form.Control
          type="password"
          size="sm"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="bg-dark text-light border-secondary"
          placeholder="Enter CivitAI API key"
        />
      </Form.Group>

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
