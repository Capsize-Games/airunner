import { useState, useEffect } from "react";
import Card from "react-bootstrap/Card";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import Tab from "react-bootstrap/Tab";
import Tabs from "react-bootstrap/Tabs";
import { getSingleton, updateSingleton } from "../../api/client";
import type { ResourceRecord } from "../../types/api";

/** Read one key from localStorage or return the provided default. */
function loadLocal<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(`airunner:${key}`);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

/** Write one key to localStorage. */
function saveLocal(key: string, value: unknown): void {
  try {
    localStorage.setItem(`airunner:${key}`, JSON.stringify(value));
  } catch { /* quota exceeded – silently ignore */ }
}

export default function SettingsView() {
  const [activeTab, setActiveTab] = useState(() => loadLocal("activeTab", "llm"));
  const [saving, setSaving] = useState(false);
  const [modelPath, setModelPath] = useState(() => loadLocal("modelPath", ""));
  const [temperature, setTemperature] = useState(() => loadLocal("temperature", 0.7));
  const [maxTokens, setMaxTokens] = useState(() => loadLocal("maxTokens", 4096));
  const [selectedVoice, setSelectedVoice] = useState(() => loadLocal("selectedVoice", ""));
  const [whisperModel, setWhisperModel] = useState(() => loadLocal("whisperModel", ""));

  useEffect(() => {
    saveLocal("activeTab", activeTab);
  }, [activeTab]);

  // Hydrate from daemon on mount (daemon takes precedence over localStorage)
  useEffect(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r: ResourceRecord) => {
        const mp = String(r.model_path ?? "");
        const t = Number(r.temperature ?? 0.7);
        const mt = Number(r.max_new_tokens ?? 4096);
        if (mp) setModelPath(mp);
        if (!Number.isNaN(t)) setTemperature(t);
        if (!Number.isNaN(mt)) setMaxTokens(mt);
      })
      .catch(() => {});
    getSingleton("VoiceSettings")
      .then((r: ResourceRecord) => {
        const v = String(r.voice ?? "");
        if (v) setSelectedVoice(v);
      })
      .catch(() => {});
    getSingleton("STTSettings")
      .then((r: ResourceRecord) => {
        const wm = String(r.model_path ?? "");
        if (wm) setWhisperModel(wm);
      })
      .catch(() => {});
  }, []);

  // Persist changes to localStorage on every change
  useEffect(() => saveLocal("modelPath", modelPath), [modelPath]);
  useEffect(() => saveLocal("temperature", temperature), [temperature]);
  useEffect(() => saveLocal("maxTokens", maxTokens), [maxTokens]);
  useEffect(() => saveLocal("selectedVoice", selectedVoice), [selectedVoice]);
  useEffect(() => saveLocal("whisperModel", whisperModel), [whisperModel]);

  const handleSaveLLM = async () => {
    setSaving(true);
    try {
      await updateSingleton("LLMGeneratorSettings", {
        model_path: modelPath,
        temperature,
        max_new_tokens: maxTokens,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveVoice = async () => {
    setSaving(true);
    try {
      await updateSingleton("VoiceSettings", { voice: selectedVoice });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSTT = async () => {
    setSaving(true);
    try {
      await updateSingleton("STTSettings", { model_path: whisperModel });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h3 className="mb-3">⚙️ Settings</h3>
      <Tabs
        activeKey={activeTab}
        onSelect={(k) => k && setActiveTab(k)}
      >
        <Tab eventKey="llm" title="LLM">
          <Card body className="mt-2">
            <Form.Group className="mb-2">
              <Form.Label>Model Path / Repo ID</Form.Label>
              <Form.Control
                value={modelPath}
                onChange={(e) => setModelPath(e.target.value)}
                placeholder="e.g. Qwen/Qwen2.5-3B-Instruct"
              />
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Temperature</Form.Label>
              <Form.Range
                min={0}
                max={2}
                step={0.1}
                value={temperature}
                onChange={(e) => setTemperature(Number(e.target.value))}
              />
              <small className="text-muted">{temperature}</small>
            </Form.Group>
            <Form.Group className="mb-2">
              <Form.Label>Max Tokens</Form.Label>
              <Form.Control
                type="number"
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
              />
            </Form.Group>
            <Button
              variant="primary"
              onClick={handleSaveLLM}
              disabled={saving}
            >
              {saving ? <Spinner animation="border" size="sm" /> : "Save LLM Settings"}
            </Button>
          </Card>
        </Tab>
        <Tab eventKey="tts" title="TTS">
          <Card body className="mt-2">
            <Form.Group className="mb-2">
              <Form.Label>Voice</Form.Label>
              <Form.Control
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                placeholder="Voice ID"
              />
            </Form.Group>
            <Button
              variant="primary"
              onClick={handleSaveVoice}
              disabled={saving}
            >
              {saving ? <Spinner animation="border" size="sm" /> : "Save Voice"}
            </Button>
          </Card>
        </Tab>
        <Tab eventKey="stt" title="STT">
          <Card body className="mt-2">
            <Form.Group className="mb-2">
              <Form.Label>Whisper Model</Form.Label>
              <Form.Control
                value={whisperModel}
                onChange={(e) => setWhisperModel(e.target.value)}
                placeholder="openai/whisper-tiny"
              />
            </Form.Group>
            <Button
              variant="primary"
              onClick={handleSaveSTT}
              disabled={saving}
            >
              {saving ? <Spinner animation="border" size="sm" /> : "Save STT Settings"}
            </Button>
          </Card>
        </Tab>
      </Tabs>
    </div>
  );
}
