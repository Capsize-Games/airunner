import { useState, useEffect, useRef } from "react";
import {
  getSingleton,
  updateSingleton,
  startArtGeneration,
  getArtJobStatus,
} from "../../api/client";
import type { ResourceRecord } from "../../types/api";
import Form from "react-bootstrap/Form";
import ProgressBar from "react-bootstrap/ProgressBar";

const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

export default function ArtPromptPanel() {
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [secondaryPrompt, setSecondaryPrompt] = useState("");
  const [secondaryNegativePrompt, setSecondaryNegativePrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(true);
  const jobIdRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getSingleton("GeneratorFormData")
      .then((r: ResourceRecord) => {
        setPrompt(String(r.prompt ?? ""));
        setNegativePrompt(String(r.negative_prompt ?? ""));
        setSecondaryPrompt(String(r.secondary_prompt ?? ""));
        setSecondaryNegativePrompt(
          String(r.secondary_negative_prompt ?? ""),
        );
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("GeneratorFormData", updates).catch(() => {});
  };

  const handleSubmit = async () => {
    if (generating || !prompt.trim()) return;
    setGenerating(true);
    setProgress(0);
    try {
      const resp = await startArtGeneration({
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || undefined,
        num_images: 1,
      });
      jobIdRef.current = resp.job_id;
      pollRef.current = setInterval(async () => {
        try {
          const status = await getArtJobStatus(resp.job_id);
          setProgress(status.progress ?? 0);
          if (status.status === "complete" || status.status === "failed") {
            handleCancel();
          }
        } catch {
          // keep polling
        }
      }, 1000);
    } catch {
      setGenerating(false);
    }
  };

  const handleCancel = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    jobIdRef.current = null;
    setGenerating(false);
    setProgress(0);
  };

  if (loading) {
    return <div className="p-2 small" style={{ color: "#a0a0a8" }}>Loading...</div>;
  }

  return (
    <div className="d-flex flex-column h-100 p-2">
      <h6 style={{ color: "#a0a0a8" }} className="mb-2 flex-shrink-0">Art Prompt</h6>

      {/* Prompt inputs — fill available space */}
      <div className="flex-grow-1 d-flex flex-column gap-2 overflow-hidden">
        <Form.Group className="flex-grow-1 d-flex flex-column" style={{ minHeight: 0 }}>
          <Form.Label className="small flex-shrink-0" style={{ color: "#a0a0a8" }}>Prompt</Form.Label>
          <Form.Control
            as="textarea"
            className="flex-grow-1"
            style={{ resize: "none", minHeight: 0 }}
            value={prompt}
            onChange={(e) => { setPrompt(e.target.value); persist({ prompt: e.target.value }); }}
            placeholder="Describe the image..."
            disabled={generating}
          />
        </Form.Group>

        <Form.Group className="flex-grow-1 d-flex flex-column" style={{ minHeight: 0 }}>
          <Form.Label className="small flex-shrink-0" style={{ color: "#a0a0a8" }}>Secondary Prompt</Form.Label>
          <Form.Control
            as="textarea"
            className="flex-grow-1"
            style={{ resize: "none", minHeight: 0 }}
            value={secondaryPrompt}
            onChange={(e) => { setSecondaryPrompt(e.target.value); persist({ secondary_prompt: e.target.value }); }}
            placeholder="Background, colors, atmosphere..."
            disabled={generating}
          />
        </Form.Group>

        <Form.Group className="flex-grow-1 d-flex flex-column" style={{ minHeight: 0 }}>
          <Form.Label className="small flex-shrink-0" style={{ color: "#a0a0a8" }}>Negative Prompt</Form.Label>
          <Form.Control
            as="textarea"
            className="flex-grow-1"
            style={{ resize: "none", minHeight: 0 }}
            value={negativePrompt}
            onChange={(e) => { setNegativePrompt(e.target.value); persist({ negative_prompt: e.target.value }); }}
            placeholder="Things to exclude..."
            disabled={generating}
          />
        </Form.Group>

        <Form.Group className="flex-grow-1 d-flex flex-column" style={{ minHeight: 0 }}>
          <Form.Label className="small flex-shrink-0" style={{ color: "#a0a0a8" }}>Sec. Negative</Form.Label>
          <Form.Control
            as="textarea"
            className="flex-grow-1"
            style={{ resize: "none", minHeight: 0 }}
            value={secondaryNegativePrompt}
            onChange={(e) => { setSecondaryNegativePrompt(e.target.value); persist({ secondary_negative_prompt: e.target.value }); }}
            disabled={generating}
          />
        </Form.Group>
      </div>

      {/* Bottom bar: progress + submit/cancel */}
      <div className="flex-shrink-0 mt-2 pt-2 border-top border-secondary">
        <div className="d-flex align-items-center gap-2">
          <div className="flex-grow-1">
            <ProgressBar
              now={progress}
              variant={generating ? "info" : "secondary"}
              style={{ height: 8 }}
              animated={generating && progress < 100}
            />
          </div>
          {generating ? (
            <button
              className="btn btn-sm btn-danger p-1"
              onClick={handleCancel}
              title="Cancel image generation"
              style={{ minWidth: 30, height: 30 }}
            >
              <img src={icon("circle-stop")} alt="Cancel" style={{ width: 16, height: 16, filter: "invert(1)" }} />
            </button>
          ) : (
            <button
              className="btn btn-sm p-1"
              style={{ background: "var(--bs-primary)", minWidth: 30, height: 30, border: "none" }}
              onClick={handleSubmit}
              disabled={!prompt.trim()}
              title="Generate image"
            >
              <img src={icon("chevron-up")} alt="Generate" style={{ width: 16, height: 16, filter: "invert(1)" }} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
