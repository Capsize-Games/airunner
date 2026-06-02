import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

type TtsEngine = "espeak" | "openvoice";

export default function TTSSection() {
  const [engine, setEngine] = useState<TtsEngine>("espeak");

  // Espeak fields
  const [espeakGender, setEspeakGender] = useState("Male");
  const [espeakVoice, setEspeakVoice] = useState("");
  const [espeakRate, setEspeakRate] = useState(100);
  const [espeakPitch, setEspeakPitch] = useState(100);
  const [espeakVolume, setEspeakVolume] = useState(100);

  // OpenVoice fields
  const [ovLanguage, setOvLanguage] = useState("EN");
  const [ovSpeed, setOvSpeed] = useState(100);
  const [ovReferencePath, setOvReferencePath] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [espeak, openvoice] = await Promise.all([
          getSingleton("EspeakSettings").catch(() => ({})),
          getSingleton("OpenVoiceSettings").catch(() => ({})),
        ]);
        if (cancelled) return;
        setEspeakGender(String(espeak.gender ?? "Male"));
        setEspeakVoice(String(espeak.voice ?? ""));
        setEspeakRate(Number(espeak.rate ?? 100));
        setEspeakPitch(Number(espeak.pitch ?? 100));
        setEspeakVolume(Number(espeak.volume ?? 100));
        setOvLanguage(String(openvoice.language ?? "EN"));
        setOvSpeed(Number(openvoice.speed ?? 100));
        setOvReferencePath(String(openvoice.reference_speaker_path ?? ""));
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
      if (engine === "espeak") {
        await updateSingleton("EspeakSettings", {
          gender: espeakGender,
          voice: espeakVoice,
          rate: espeakRate,
          pitch: espeakPitch,
          volume: espeakVolume,
        } as Record<string, unknown>);
      } else {
        await updateSingleton("OpenVoiceSettings", {
          language: ovLanguage,
          speed: ovSpeed,
          reference_speaker_path: ovReferencePath,
        } as Record<string, unknown>);
      }
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
      <h6 className="mb-3">Text-to-Speech</h6>

      <Form.Group className="mb-3">
        <Form.Label className="small">TTS Engine</Form.Label>
        <Form.Select
          size="sm"
          value={engine}
          onChange={(e) => setEngine(e.target.value as TtsEngine)}
          className="bg-dark text-light border-secondary"
        >
          <option value="espeak">eSpeak</option>
          <option value="openvoice">OpenVoice</option>
        </Form.Select>
      </Form.Group>

      {engine === "espeak" ? (
        <>
          <Form.Group className="mb-2">
            <Form.Label className="small">Gender</Form.Label>
            <Form.Select
              size="sm"
              value={espeakGender}
              onChange={(e) => setEspeakGender(e.target.value)}
              className="bg-dark text-light border-secondary"
            >
              <option value="Male">Male</option>
              <option value="Female">Female</option>
            </Form.Select>
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label className="small">Voice</Form.Label>
            <Form.Control
              size="sm"
              value={espeakVoice}
              onChange={(e) => setEspeakVoice(e.target.value)}
              className="bg-dark text-light border-secondary"
              placeholder="e.g. english (america)"
            />
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label className="small">
              Rate: {espeakRate}
            </Form.Label>
            <Form.Range
              min={0}
              max={300}
              step={1}
              value={espeakRate}
              onChange={(e) => setEspeakRate(Number(e.target.value))}
            />
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label className="small">
              Pitch: {espeakPitch}
            </Form.Label>
            <Form.Range
              min={1}
              max={100}
              step={1}
              value={espeakPitch}
              onChange={(e) => setEspeakPitch(Number(e.target.value))}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label className="small">
              Volume: {espeakVolume}
            </Form.Label>
            <Form.Range
              min={1}
              max={100}
              step={1}
              value={espeakVolume}
              onChange={(e) => setEspeakVolume(Number(e.target.value))}
            />
          </Form.Group>
        </>
      ) : (
        <>
          <Form.Group className="mb-2">
            <Form.Label className="small">Language</Form.Label>
            <Form.Select
              size="sm"
              value={ovLanguage}
              onChange={(e) => setOvLanguage(e.target.value)}
              className="bg-dark text-light border-secondary"
            >
              <option value="EN">English</option>
              <option value="JA">Japanese</option>
              <option value="ZH">Chinese</option>
              <option value="KO">Korean</option>
            </Form.Select>
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Label className="small">
              Speed: {ovSpeed}
            </Form.Label>
            <Form.Range
              min={1}
              max={100}
              step={1}
              value={ovSpeed}
              onChange={(e) => setOvSpeed(Number(e.target.value))}
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label className="small">
              Reference Speaker Path
            </Form.Label>
            <Form.Control
              size="sm"
              value={ovReferencePath}
              onChange={(e) => setOvReferencePath(e.target.value)}
              className="bg-dark text-light border-secondary"
              placeholder="/path/to/voice/sample.mp3"
            />
          </Form.Group>
        </>
      )}

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
