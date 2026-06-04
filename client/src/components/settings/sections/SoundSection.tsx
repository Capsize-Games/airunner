import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

export default function SoundSection() {
  const [micVolume, setMicVolume] = useState(50);
  const [loading, setLoading] = useState(true);

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

  function handleMicVolumeChange(value: number) {
    setMicVolume(value);
    updateSingleton("SoundSettings", {
      microphone_volume: value,
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
          onChange={(e) => handleMicVolumeChange(Number(e.target.value))}
        />
      </Form.Group>
    </div>
  );
}
