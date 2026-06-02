import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../api/client";

export default function ImageExportSection() {
  const [autoExport, setAutoExport] = useState(true);
  const [exportType, setExportType] = useState("png");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const appSettings = await getSingleton("ApplicationSettings");
        if (cancelled) return;
        setAutoExport(appSettings.auto_export_images !== false);
        setExportType(String(appSettings.image_export_type ?? "png"));
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
        auto_export_images: autoExport,
        image_export_type: exportType,
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
      <h6 className="mb-3">Image Export</h6>

      <Form.Group className="mb-2">
        <Form.Check
          type="switch"
          label="Automatically export images"
          checked={autoExport}
          onChange={(e) => setAutoExport(e.target.checked)}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-3">
        <Form.Label className="small">Image type</Form.Label>
        <Form.Select
          size="sm"
          value={exportType}
          onChange={(e) => setExportType(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="png">PNG</option>
          <option value="jpeg">JPEG</option>
          <option value="webp">WebP</option>
        </Form.Select>
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
