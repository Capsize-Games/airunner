import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getPrivacySettings,
  updatePrivacySettings,
} from "../../../api/client";

export default function OpenRouterSection() {
  const [allowOpenrouter, setAllowOpenrouter] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const privacy = await getPrivacySettings();
        if (cancelled) return;
        setAllowOpenrouter(privacy.services?.openrouter !== false);
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
    setAllowOpenrouter(checked);
    updatePrivacySettings({ openrouter: checked }).catch(() => {});
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
      <h6 className="mb-3">OpenRouter</h6>

      <Form.Group className="mb-3">
        <Form.Check
          type="switch"
          label="Allow OpenRouter API"
          checked={allowOpenrouter}
          onChange={(e) => handleToggle(e.target.checked)}
          className="small"
        />
      </Form.Group>
    </div>
  );
}
