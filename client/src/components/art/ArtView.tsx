import { useState, useEffect } from "react";
import Card from "react-bootstrap/Card";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Alert from "react-bootstrap/Alert";
import Spinner from "react-bootstrap/Spinner";
import Image from "react-bootstrap/Image";
import {
  startArtGeneration,
  getArtJobStatus,
  getHardwareProfile,
} from "../../api/client";
import type {
  ArtJobStatus,
  HardwareProfile,
} from "../../types/api";

export default function ArtView() {
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [steps, setSteps] = useState(20);
  const [cfgScale, setCfgScale] = useState(7.5);
  const [seed, setSeed] = useState<number | undefined>(undefined);
  const [numImages, setNumImages] = useState(1);
  const [generating, setGenerating] = useState(false);
  const [status, setStatus] = useState<ArtJobStatus | null>(null);
  const [images, setImages] = useState<string[]>([]);
  const [hw, setHw] = useState<HardwareProfile | null>(null);
  const [selectedVersion, setSelectedVersion] = useState("SDXL 1.0");

  useEffect(() => {
    getHardwareProfile().then(setHw).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    if (!prompt.trim() || generating) return;
    setGenerating(true);
    setStatus(null);
    setImages([]);

    try {
      const { job_id } = await startArtGeneration({
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || undefined,
        steps,
        cfg_scale: cfgScale,
        seed,
        num_images: numImages,
        version: selectedVersion || undefined,
      });

      let done = false;
      while (!done) {
        await new Promise((r) => setTimeout(r, 200));
        const st = await getArtJobStatus(job_id);
        setStatus(st);
        if (["completed", "failed", "cancelled"].includes(st.status)) {
          done = true;
        }
      }
    } catch (err: unknown) {
      setStatus({
        status: "failed",
        progress: 0,
        error: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <h3 className="mb-3">🎨 Art Generation</h3>
      {hw ? (
        <small className="text-muted">
          GPU: {hw.device_name ?? "None"} · VRAM: {hw.available_vram_gb.toFixed(1)}/{hw.total_vram_gb.toFixed(1)} GB
        </small>
      ) : null}

      <Row className="mt-3">
        <Col md={4}>
          <Card className="mb-3">
            <Card.Body>
              <Form.Group className="mb-2">
                <Form.Label>Version</Form.Label>
                <Form.Select
                  value={selectedVersion}
                  onChange={(e) => setSelectedVersion(e.target.value)}
                >
                  <option value="SDXL 1.0">SDXL 1.0</option>
                  <option value="SDXL Turbo">SDXL Turbo</option>
                  <option value="Z-Image Turbo">Z-Image Turbo</option>
                </Form.Select>
              </Form.Group>
              <Form.Group className="mb-2">
                <Form.Label>Steps</Form.Label>
                <Form.Range min={1} max={50} value={steps} onChange={(e) => setSteps(Number(e.target.value))} />
                <small className="text-muted">{steps}</small>
              </Form.Group>
              <Form.Group className="mb-2">
                <Form.Label>CFG Scale</Form.Label>
                <Form.Range min={1} max={20} step={0.5} value={cfgScale} onChange={(e) => setCfgScale(Number(e.target.value))} />
                <small className="text-muted">{cfgScale}</small>
              </Form.Group>
              <Form.Group className="mb-2">
                <Form.Label>Images</Form.Label>
                <Form.Select value={numImages} onChange={(e) => setNumImages(Number(e.target.value))}>
                  {[1, 2, 4].map((n) => (<option key={n} value={n}>{n}</option>))}
                </Form.Select>
              </Form.Group>
              <Form.Group className="mb-2">
                <Form.Label>Seed (optional)</Form.Label>
                <Form.Control type="number" placeholder="Random" value={seed ?? ""} onChange={(e) => setSeed(e.target.value ? Number(e.target.value) : undefined)} />
              </Form.Group>
            </Card.Body>
          </Card>
        </Col>
        <Col md={8}>
          <Form.Group className="mb-2">
            <Form.Label>Prompt</Form.Label>
            <Form.Control as="textarea" rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Describe the image you want to generate..." />
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Label>Negative Prompt</Form.Label>
            <Form.Control as="textarea" rows={2} value={negativePrompt} onChange={(e) => setNegativePrompt(e.target.value)} placeholder="What to avoid..." />
          </Form.Group>
          <Button variant="primary" onClick={handleGenerate} disabled={generating || !prompt.trim()} className="mb-3 w-100">
            {generating ? (<><Spinner animation="border" size="sm" /> Generating...</>) : ("Generate")}
          </Button>
          {status ? (
            <Alert variant={status.status === "completed" ? "success" : status.status === "failed" ? "danger" : "info"}>
              {status.status === "completed" ? "✅ Generated successfully!" : status.error ?? `Status: ${status.status} (${status.progress}%)`}
            </Alert>
          ) : null}
          {images.map((src, i) => (<Image key={i} src={src} fluid rounded className="mb-2" />))}
        </Col>
      </Row>
    </div>
  );
}
