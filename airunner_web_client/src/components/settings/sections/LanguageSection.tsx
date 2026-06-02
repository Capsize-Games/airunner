import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

export default function LanguageSection() {
  const [detectedLanguage, setDetectedLanguage] = useState("en");
  const [userLanguage, setUserLanguage] = useState("en");
  const [botLanguage, setBotLanguage] = useState("en");
  const [loading, setLoading] = useState(true);

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

  function handleDetectedLanguageChange(value: string) {
    setDetectedLanguage(value);
    updateSingleton("ApplicationSettings", {
      detected_language: value,
    } as Record<string, unknown>).catch(() => {});
  }

  function handleUserLanguageChange(value: string) {
    setUserLanguage(value);
    updateSingleton("LanguageSettings", {
      user_language: value,
      bot_language: botLanguage,
    } as Record<string, unknown>).catch(() => {});
  }

  function handleBotLanguageChange(value: string) {
    setBotLanguage(value);
    updateSingleton("LanguageSettings", {
      user_language: userLanguage,
      bot_language: value,
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
      <h6 className="mb-3">Language Settings</h6>

      <Form.Group className="mb-2">
        <Form.Label className="small">GUI Language</Form.Label>
        <Form.Select
          size="sm"
          value={detectedLanguage}
          onChange={(e) => handleDetectedLanguageChange(e.target.value)}
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
          onChange={(e) => handleUserLanguageChange(e.target.value)}
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
          onChange={(e) => handleBotLanguageChange(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="en">English</option>
          <option value="ja">Japanese</option>
        </Form.Select>
      </Form.Group>
    </div>
  );
}
