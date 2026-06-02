import { useState, useEffect, useRef } from "react";
import {
  startArtGeneration,
  getArtJobStatus,
} from "../../api/client";
import Form from "react-bootstrap/Form";
import ProgressBar from "react-bootstrap/ProgressBar";

const STORAGE_KEY = "airunner_art_prompt_data";
const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

interface PromptData {
  prompt: string;
  negative_prompt: string;
  secondary_prompt: string;
  secondary_negative_prompt: string;
}

const DEFAULT_PROMPT_DATA: PromptData = {
  prompt: "",
  negative_prompt: "",
  secondary_prompt: "",
  secondary_negative_prompt: "",
};

function loadPromptData(): PromptData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as PromptData;
  } catch { /* ignore */ }
  return { ...DEFAULT_PROMPT_DATA };
}

function savePromptData(data: Record<string, string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch { /* ignore */ }
}

export default function ArtPromptPanel() {
  const initial = loadPromptData();
  const [prompt, setPrompt] = useState(initial.prompt);
  const [negativePrompt, setNegativePrompt] = useState(initial.negative_prompt);
  const [secondaryPrompt, setSecondaryPrompt] = useState(initial.secondary_prompt);
  const [secondaryNegativePrompt, setSecondaryNegativePrompt] = useState(initial.secondary_negative_prompt);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const jobIdRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isZImage, setIsZImage] = useState(false);

  useEffect(() => {
    // Listen for art version changes from ArtModelPanel
    const handler = (e: Event) => {
      const version = (e as CustomEvent).detail as string;
      setIsZImage(version === "Z-Image Turbo");
    };
    window.addEventListener("art-version-changed", handler);
    return () => {
      window.removeEventListener("art-version-changed", handler);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const persist = (updates: Record<string, string>) => {
    const current = loadPromptData();
    savePromptData({ ...current, ...updates });
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

        {!isZImage && (
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
        )}

        {!isZImage && (
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
        )}

        {!isZImage && (
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
        )}
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
