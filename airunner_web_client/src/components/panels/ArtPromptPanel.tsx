import { useState, useEffect, useRef, useCallback } from "react";
import {
  startArtGeneration,
  getArtJobStatus,
} from "../../api/client";
import Form from "react-bootstrap/Form";
import ProgressBar from "react-bootstrap/ProgressBar";
import ArtModelSelector from "../shared/ArtModelSelector";

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
  const savedVersion = (() => {
    try { return localStorage.getItem("airunner_art_version") || ""; }
    catch { return ""; }
  })();

  const [prompt, setPrompt] = useState(initial.prompt);
  const [negativePrompt, setNegativePrompt] = useState(
    initial.negative_prompt,
  );
  const [secondaryPrompt, setSecondaryPrompt] = useState(
    initial.secondary_prompt,
  );
  const [secondaryNegativePrompt, setSecondaryNegativePrompt] = useState(
    initial.secondary_negative_prompt,
  );
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const jobIdRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [artVersion, setArtVersion] = useState(savedVersion);
  const [artModel, setArtModel] = useState(() => {
    try { return localStorage.getItem("airunner_art_model") || ""; }
    catch { return ""; }
  });
  const [isZImage, setIsZImage] = useState(
    savedVersion === "Z-Image Turbo",
  );
  const [activeLoras, setActiveLoras] = useState<
    { id: number; name: string }[]
  >([]);
  const [activeEmbeddings, setActiveEmbeddings] = useState<
    { id: number; name: string }[]
  >([]);

  const reloadActiveLoras = useCallback(async () => {
    try {
      const { listLoras } = await import("../../api/client");
      const data = await listLoras();
      const version = (() => {
        try {
          return localStorage.getItem("airunner_art_version") || "";
        } catch { return ""; }
      })();
      const enabled = (data.loras ?? [])
        .filter((l) => l.enabled)
        .filter((l) =>
          version ? l.path.includes(`/${version}/`) : true,
        )
        .map((l) => ({ id: l.id, name: l.name }));
      setActiveLoras(enabled);
    } catch { /* */ }
  }, []);

  const reloadActiveEmbeddings = useCallback(async () => {
    try {
      const { listEmbeddings } = await import("../../api/client");
      const data = await listEmbeddings();
      const version = (() => {
        try {
          return localStorage.getItem("airunner_art_version") || "";
        } catch { return ""; }
      })();
      const enabled = (data.embeddings ?? [])
        .filter((e) => e.enabled)
        .filter((e) =>
          version ? e.path.includes(`/${version}/`) : true,
        )
        .map((e) => ({ id: e.id, name: e.name }));
      setActiveEmbeddings(enabled);
    } catch { /* */ }
  }, []);

  useEffect(() => {
    const versionHandler = (e: Event) => {
      const v = (e as CustomEvent).detail as string;
      setArtVersion(v);
      setIsZImage(v === "Z-Image Turbo");
      reloadActiveLoras();
      reloadActiveEmbeddings();
    };
    const modelHandler = (e: Event) => {
      const m = (e as CustomEvent).detail as string;
      setArtModel(m ?? "");
    };
    window.addEventListener("art-version-changed", versionHandler);
    window.addEventListener("art-model-changed", modelHandler);
    try {
      const m = localStorage.getItem("airunner_art_model");
      if (m) setArtModel(m);
    } catch {}
    return () => {
      window.removeEventListener(
        "art-version-changed", versionHandler,
      );
      window.removeEventListener("art-model-changed", modelHandler);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [reloadActiveLoras, reloadActiveEmbeddings]);

  // Load initially + listen for LoRA changes
  useEffect(() => {
    reloadActiveLoras();
    const handler = () => reloadActiveLoras();
    window.addEventListener("lora-changed", handler);
    return () => window.removeEventListener("lora-changed", handler);
  }, [reloadActiveLoras]);

  // Listen for embedding changes
  useEffect(() => {
    reloadActiveEmbeddings();
    const handler = () => reloadActiveEmbeddings();
    window.addEventListener("embedding-changed", handler);
    return () =>
      window.removeEventListener("embedding-changed", handler);
  }, [reloadActiveEmbeddings]);

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
          if (
            status.status === "complete" ||
            status.status === "failed"
          ) {
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

  const deactivateLora = (id: number) => {
    import("../../api/client").then(({ updateLora }) => {
      updateLora(id, { enabled: false })
        .then(() => {
          setActiveLoras((prev) =>
            prev.filter((l) => l.id !== id),
          );
          window.dispatchEvent(
            new CustomEvent("lora-changed", {
              detail: { id, enabled: false },
            }),
          );
        })
        .catch(() => {});
    });
  };

  const deactivateEmbedding = (id: number) => {
    import("../../api/client").then(({ updateEmbedding }) => {
      updateEmbedding(id, { enabled: false })
        .then(() => {
          setActiveEmbeddings((prev) =>
            prev.filter((e) => e.id !== id),
          );
          window.dispatchEvent(
            new CustomEvent("embedding-changed", {
              detail: { id, enabled: false },
            }),
          );
        })
        .catch(() => {});
    });
  };

  return (
    <div className="d-flex flex-column h-100 p-2">
      <h6 style={{ color: "var(--theme-text-secondary)" }}
        className="mb-2 flex-shrink-0"
      >
        Art Prompt
      </h6>

      <div className="flex-grow-1 d-flex flex-column gap-2
                      overflow-hidden"
      >
        <Form.Group
          className="flex-grow-1 d-flex flex-column"
          style={{ minHeight: 0 }}
        >
          <Form.Label
            className="small flex-shrink-0"
            style={{ color: "var(--theme-text-secondary)" }}
          >
            Prompt
          </Form.Label>
          <Form.Control
            as="textarea"
            className="flex-grow-1"
            style={{ resize: "none", minHeight: 0 }}
            value={prompt}
            onChange={(e) => {
              setPrompt(e.target.value);
              persist({ prompt: e.target.value });
            }}
            placeholder="Describe the image..."
            disabled={generating}
          />
        </Form.Group>

        {!isZImage && (
          <Form.Group
            className="flex-grow-1 d-flex flex-column"
            style={{ minHeight: 0 }}
          >
            <Form.Label
              className="small flex-shrink-0"
              style={{ color: "var(--theme-text-secondary)" }}
            >
              Secondary Prompt
            </Form.Label>
            <Form.Control
              as="textarea"
              className="flex-grow-1"
              style={{ resize: "none", minHeight: 0 }}
              value={secondaryPrompt}
              onChange={(e) => {
                setSecondaryPrompt(e.target.value);
                persist({ secondary_prompt: e.target.value });
              }}
              placeholder="Background, colors, atmosphere..."
              disabled={generating}
            />
          </Form.Group>
        )}

        {!isZImage && (
          <Form.Group
            className="flex-grow-1 d-flex flex-column"
            style={{ minHeight: 0 }}
          >
            <Form.Label
              className="small flex-shrink-0"
              style={{ color: "var(--theme-text-secondary)" }}
            >
              Negative Prompt
            </Form.Label>
            <Form.Control
              as="textarea"
              className="flex-grow-1"
              style={{ resize: "none", minHeight: 0 }}
              value={negativePrompt}
              onChange={(e) => {
                setNegativePrompt(e.target.value);
                persist({ negative_prompt: e.target.value });
              }}
              placeholder="Things to exclude..."
              disabled={generating}
            />
          </Form.Group>
        )}

        {!isZImage && (
          <Form.Group
            className="flex-grow-1 d-flex flex-column"
            style={{ minHeight: 0 }}
          >
            <Form.Label
              className="small flex-shrink-0"
              style={{ color: "var(--theme-text-secondary)" }}
            >
              Sec. Negative
            </Form.Label>
            <Form.Control
              as="textarea"
              className="flex-grow-1"
              style={{ resize: "none", minHeight: 0 }}
              value={secondaryNegativePrompt}
              onChange={(e) => {
                setSecondaryNegativePrompt(e.target.value);
                persist({
                  secondary_negative_prompt: e.target.value,
                });
              }}
              disabled={generating}
            />
          </Form.Group>
        )}
      </div>

      <div className="flex-shrink-0 mt-2">
        {/* Active embedding pills */}
        {activeEmbeddings.length > 0 && (
          <div
            className="mb-1 p-2 rounded"
            style={{
              background: "rgba(0,132,185,0.05)",
              border: "1px solid rgba(0,132,185,0.25)",
            }}
          >
            <small
              style={{
                color: "#0084b8",
                display: "block",
                marginBottom: 4,
                fontSize: "0.65rem",
                fontWeight: 700,
              }}
            >
              Active Embeddings
            </small>
            <div className="d-flex flex-wrap gap-1">
              {activeEmbeddings.map((emb) => (
                <span
                  key={emb.id}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    background: "rgba(0,132,185,0.2)",
                    border: "1px solid #0084b8",
                    borderRadius: 12,
                    padding: "2px 8px",
                    fontSize: "0.7rem",
                    color: "var(--theme-text)",
                  }}
                >
                  <span
                    style={{
                      cursor: "pointer",
                      color: "#ff5555",
                      fontSize: "0.7rem",
                      lineHeight: 1,
                    }}
                    onClick={() => deactivateEmbedding(emb.id)}
                    title="Deactivate embedding"
                  >
                    ✕
                  </span>
                  {emb.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Active LoRA pills */}
        {activeLoras.length > 0 && (
          <div
            className="mb-1 p-2 rounded"
            style={{
              background: "rgba(185,0,132,0.05)",
              border: "1px solid rgba(184,0,132,0.25)",
            }}
          >
            <small
              style={{
                color: "#b80084",
                display: "block",
                marginBottom: 4,
                fontSize: "0.65rem",
                fontWeight: 700,
              }}
            >
              Active LoRA
            </small>
            <div className="d-flex flex-wrap gap-1">
              {activeLoras.map((lora) => (
                <span
                  key={lora.id}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    background: "rgba(185,0,132,0.2)",
                    border: "1px solid #b80084",
                    borderRadius: 12,
                    padding: "2px 8px",
                    fontSize: "0.7rem",
                    color: "var(--theme-text)",
                  }}
                >
                  <span
                    style={{
                      cursor: "pointer",
                      color: "#ff5555",
                      fontSize: "0.7rem",
                      lineHeight: 1,
                    }}
                    onClick={() => deactivateLora(lora.id)}
                    title="Deactivate LoRA"
                  >
                    ✕
                  </span>
                  {lora.name}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mb-1">
          <ArtModelSelector
            version={artVersion}
            modelPath={artModel}
            onVersionChange={(v) => {
              setArtVersion(v);
              setArtModel("");
              setIsZImage(v === "Z-Image Turbo");
            }}
            onModelChange={(m) => setArtModel(m)}
          />
        </div>
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
              <img
                src={icon("circle-stop")}
                alt="Cancel"
                style={{
                  width: 16,
                  height: 16,
                  filter: "invert(1)",
                }}
              />
            </button>
          ) : (
            <button
              className="btn btn-sm p-1"
              style={{
                background: "var(--bs-primary)",
                minWidth: 30,
                height: 30,
                border: "none",
              }}
              onClick={handleSubmit}
              disabled={!prompt.trim()}
              title="Generate image"
            >
              <img
                src={icon("chevron-up")}
                alt="Generate"
                style={{
                  width: 16,
                  height: 16,
                  filter: "invert(1)",
                }}
              />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
