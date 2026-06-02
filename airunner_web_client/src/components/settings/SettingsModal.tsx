import { useState, useEffect } from "react";
import { getArtModelOptions } from "../../api/client";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";

export default function SettingsModal({
  onClose,
}: {
  onClose: () => void;
}) {
  const [theme, setTheme] = useState("dark");
  const [language, setLanguage] = useState("en");
  const [precisions, setPrecisions] = useState<
    { label: string; value: string }[]
  >([]);
  const [defaultPrecision, setDefaultPrecision] = useState("");

  useEffect(() => {
    getArtModelOptions()
      .then((opts) => {
        setPrecisions(opts.precisions ?? []);
      })
      .catch(() => {});
  }, []);

  const sectionClass =
    "bg-dark bg-opacity-25 rounded p-2 mb-2 border border-secondary";

  return (
    <div className="settings-modal-backdrop" onClick={onClose}>
      <div
        className="settings-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
      >
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5 className="mb-0">Settings</h5>
          <Button
            variant="link"
            className="text-light p-0"
            onClick={onClose}
            size="sm"
          >
            ✕
          </Button>
        </div>

        {/* Appearance */}
        <div className={sectionClass}>
          <h6 className="small text-muted mb-2">Appearance</h6>
          <Form.Group className="mb-2">
            <Form.Label className="small text-muted">Theme</Form.Label>
            <Form.Select
              size="sm"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="bg-dark text-light border-secondary"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </Form.Select>
          </Form.Group>
        </div>

        {/* Language */}
        <div className={sectionClass}>
          <h6 className="small text-muted mb-2">Language</h6>
          <Form.Group className="mb-2">
            <Form.Label className="small text-muted">
              Interface Language
            </Form.Label>
            <Form.Select
              size="sm"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-dark text-light border-secondary"
            >
              <option value="en">English</option>
              <option value="ja">Japanese</option>
            </Form.Select>
          </Form.Group>
        </div>

        {/* Default Precision */}
        {precisions.length > 0 && (
          <div className={sectionClass}>
            <h6 className="small text-muted mb-2">
              Model Defaults
            </h6>
            <Form.Group className="mb-2">
              <Form.Label className="small text-muted">
                Default Precision
              </Form.Label>
              <Form.Select
                size="sm"
                value={defaultPrecision}
                onChange={(e) =>
                  setDefaultPrecision(e.target.value)
                }
                className="bg-dark text-light border-secondary"
              >
                <option value="">System default</option>
                {precisions.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>
        )}

        {/* Privacy */}
        <div className={sectionClass}>
          <h6 className="small text-muted mb-2">Privacy</h6>
          <Form.Group className="mb-2">
            <Form.Check
              type="switch"
              label="Enable HuggingFace downloads"
              defaultChecked
              className="small text-muted"
            />
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Check
              type="switch"
              label="Enable CivitAI downloads"
              defaultChecked
              className="small text-muted"
            />
          </Form.Group>
        </div>

        {/* Keyboard Shortcuts */}
        <div className={sectionClass}>
          <h6 className="small text-muted mb-2">
            Keyboard Shortcuts
          </h6>
          <p className="small text-muted mb-0">
            View and configure keyboard shortcuts for common
            actions.
          </p>
        </div>
      </div>
    </div>
  );
}
