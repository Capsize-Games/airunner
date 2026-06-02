import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../api/client";

export default function LanguageSection() {
  const [detectedLanguage, setDetectedLanguage] = useState("en");
  const [userLanguage, setUserLanguage] = useState("en");
  const [botLanguage, setBotLanguage] = useState("en");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [appSettings, langSettings] = await Promise.all([
          getSingleton("ApplicationSettings"),
          getSingleton("LanguageSettings"),
        ]);
        if (cancelled) return;
        setDetectedLanguage(String(appSettings.detected_language ?? "en"));
        setUserLanguage(String(langSettings.user_language ?? "en"));
        setBotLanguage(String(langSettings.bot_language ?? "en"));
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
        updateSingleton("ApplicationSettings", {
          detected_language: detectedLanguage,
        } as Record<string, unknown>),
        updateSingleton("LanguageSettings", {
          user_language: userLanguage,
          bot_language: botLanguage,
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
      <h6 className="mb-3">Language Settings</h6>

      <Form.Group className="mb-2">
        <Form.Label className="small">GUI Language</Form.Label>
        <Form.Select
          size="sm"
          value={detectedLanguage}
          onChange={(e) => setDetectedLanguage(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="en">English</option>
          <option value="ja">Japanese</option>
        </Form.Select>
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small">User Language</Form.Label>
        <Form.Select
          size="sm"
          value={userLanguage}
          onChange={(e) => setUserLanguage(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="en">English</option>
          <option value="ja">Japanese</option>
        </Form.Select>
      </Form.Group>

      <Form.Group className="mb-3">
        <Form.Label className="small">Bot Language</Form.Label>
        <Form.Select
          size="sm"
          value={botLanguage}
          onChange={(e) => setBotLanguage(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="en">English</option>
          <option value="ja">Japanese</option>
        </Form.Select>
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
