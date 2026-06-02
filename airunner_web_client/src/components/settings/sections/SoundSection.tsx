import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

export default function SoundSection() {
  const [micVolume, setMicVolume] = useState(50);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const sound = await getSingleton("SoundSettings");
        if (cancelled) return;
        setMicVolume(Number(sound.microphone_volume ?? 50));
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
      await updateSingleton("SoundSettings", {
        microphone_volume: micVolume,
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
      <h6 className="mb-3">Sound Settings</h6>

      <Form.Group className="mb-3">
        <Form.Label className="small">
          Microphone Volume: {micVolume}
        </Form.Label>
        <Form.Range
          min={0}
          max={100}
          step={1}
          value={micVolume}
          onChange={(e) => setMicVolume(Number(e.target.value))}
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
