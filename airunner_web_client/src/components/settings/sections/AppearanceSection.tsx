import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

export default function AppearanceSection() {
  const [darkMode, setDarkMode] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const appSettings = await getSingleton("ApplicationSettings");
        if (cancelled) return;
        setDarkMode(appSettings.dark_mode_enabled_db !== false);
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function handleThemeChange(value: string) {
    const isDark = value === "dark";
    setDarkMode(isDark);
    updateSingleton("ApplicationSettings", {
      dark_mode_enabled_db: isDark,
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
      <h6 className="mb-3">Theme</h6>

      <Form.Group className="mb-2">
        <Form.Label className="small">Theme</Form.Label>
        <Form.Select
          size="sm"
          value={darkMode ? "dark" : "light"}
          onChange={(e) => handleThemeChange(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="dark">Dark</option>
          <option value="light">Light</option>
        </Form.Select>
      </Form.Group>
    </div>
  );
}
