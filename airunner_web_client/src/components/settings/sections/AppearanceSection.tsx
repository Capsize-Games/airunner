import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

export default function AppearanceSection() {
  const [darkMode, setDarkMode] = useState(true);
  const [checkUpdates, setCheckUpdates] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const appSettings = await getSingleton("ApplicationSettings");
        if (cancelled) return;
        setDarkMode(appSettings.dark_mode_enabled !== false);
        setCheckUpdates(appSettings.latest_version_check !== false);
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
      await updateSingleton("ApplicationSettings", {
        dark_mode_enabled: darkMode,
        latest_version_check: checkUpdates,
      } as Record<string, unknown>);
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
      <h6 className="mb-3">Appearance</h6>

      <Form.Group className="mb-2">
        <Form.Label className="small">Theme</Form.Label>
        <Form.Select
          size="sm"
          value={darkMode ? "dark" : "light"}
          onChange={(e) => setDarkMode(e.target.value === "dark")}
          className="bg-dark text-light border-secondary"
        >
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </Form.Select>
      </Form.Group>

      <Form.Group className="mb-3">
        <Form.Check
          type="switch"
          label="Check for updates"
          checked={checkUpdates}
          onChange={(e) => setCheckUpdates(e.target.checked)}
          className="small"
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
