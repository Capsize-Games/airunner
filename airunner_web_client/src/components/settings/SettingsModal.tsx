import { useState } from "react";

export default function SettingsModal({
  onClose,
}: {
  onClose: () => void;
}) {
  const [theme, setTheme] = useState("dark");
  const [language, setLanguage] = useState("en");

  return (
    <div className="settings-modal-backdrop" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h5>Settings</h5>
          <button className="btn-close btn-close-white" onClick={onClose} />
        </div>

        <div className="mb-2">
          <label className="form-label small">Theme</label>
          <select
            className="form-select form-select-sm"
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            style={{ background: "#1a1a2e", color: "#c8c8c8", borderColor: "#333" }}
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </div>

        <div className="mb-2">
          <label className="form-label small">Language</label>
          <select
            className="form-select form-select-sm"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{ background: "#1a1a2e", color: "#c8c8c8", borderColor: "#333" }}
          >
            <option value="en">English</option>
            <option value="ja">Japanese</option>
          </select>
        </div>
      </div>
    </div>
  );
}
