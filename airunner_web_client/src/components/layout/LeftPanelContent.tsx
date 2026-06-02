import { useState, useEffect, useCallback } from "react";
import {
  listConversations,
  createConversation,
  deleteConversation,
  getSingleton,
  updateSingleton,
  getBootstrap,
  getArtOptions,
  listLLMModels,
} from "../../api/client";
import type {
  Conversation,
  ResourceRecord,
} from "../../types/api";
import Spinner from "react-bootstrap/Spinner";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import ListGroup from "react-bootstrap/ListGroup";

// ── Knowledge Base ──
export function KnowledgeBasePanel() {
  const [documents, setDocuments] = useState<
    { id: number; name: string; path: string; indexed: boolean }[]
  >([]);
  const [totalDocs, setTotalDocs] = useState(0);
  const [indexedDocs, setIndexedDocs] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch document statistics from settings domain
    getSingleton("DocumentCollection")
      .then((r: ResourceRecord) => {
          const total = Number(r.total ?? 0);
          const indexed = Number(r.indexed ?? 0);
          setTotalDocs(total);
          setIndexedDocs(indexed);
        })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Knowledge Base</h6>

      {loading ? (
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      ) : (
        <>
          <div className="row g-2 mb-2">
            <div className="col-4">
              <div className="bg-dark rounded p-1 text-center">
                <small className="text-muted d-block">Total</small>
                <strong className="small">{totalDocs}</strong>
              </div>
            </div>
            <div className="col-4">
              <div className="bg-dark rounded p-1 text-center">
                <small className="text-muted d-block">Indexed</small>
                <strong className="small text-success">
                  {indexedDocs}
                </strong>
              </div>
            </div>
            <div className="col-4">
              <div className="bg-dark rounded p-1 text-center">
                <small className="text-muted d-block">Pending</small>
                <strong className="small text-warning">
                  {totalDocs - indexedDocs}
                </strong>
              </div>
            </div>
          </div>

          <div className="kb-toolbar">
            <button title="Import document(s) into knowledge base">
              <img src="/icons/lucide/dark/upload.svg" alt="Import" />
            </button>
            <button title="Index all documents">
              <img src="/icons/lucide/dark/database.svg" alt="Index" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Chat History ──
export function ChatHistoryPanel({
  onSelectConversation,
}: {
  onSelectConversation: (id: number) => void;
}) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await listConversations(50);
      setConversations(data.conversations ?? []);
    } catch {
      // daemon not available
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleDelete = async (id: number) => {
    try {
      await deleteConversation(id);
      await refresh();
    } catch {
      // ignore
    }
  };

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">Chat History</h6>
        <Button
          size="sm"
          variant="outline-danger"
          onClick={() =>
            conversations.forEach((c) => handleDelete(c.id))
          }
        >
          Clear All
        </Button>
      </div>

      {loading ? (
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      ) : conversations.length === 0 ? (
        <p className="text-muted small">
          No conversations yet. Start a chat to create one.
        </p>
      ) : (
        <ListGroup variant="flush">
          {conversations.map((c) => (
            <ListGroup.Item
              key={c.id}
              action
              active={c.current}
              className="d-flex justify-content-between align-items-center py-1 px-2 bg-transparent"
              onClick={() => onSelectConversation(c.id)}
            >
              <small className="text-truncate">
                {c.title || `Chat #${c.id}`}
              </small>
              <Button
                variant="link"
                size="sm"
                className="text-danger p-0 ms-1"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(c.id);
                }}
                title="Delete"
              >
                ✕
              </Button>
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
    </div>
  );
}

// ── LLM Settings ──
export function LLMSettingsPanel() {
  const [modelPath, setModelPath] = useState("");
  const [modelService, setModelService] = useState("local");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [precision, setPrecision] = useState("");
  const [precisionOptions, setPrecisionOptions] = useState<
    { label: string; value: string }[]
  >([]);
  const [localModels, setLocalModels] = useState<
    { label: string; value: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const isLocal = modelService === "local";

  useEffect(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r: ResourceRecord) => {
        setModelPath(String(r.model_path ?? ""));
        setModelService(String(r.model_service ?? "local"));
        setTemperature(Number(r.temperature ?? 0.7));
        setMaxTokens(Number(r.max_new_tokens ?? 4096));
        setPrecision(String(r.dtype ?? ""));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    getArtOptions()
      .then((opts) => setPrecisionOptions(opts.precisions ?? []))
      .catch(() => {});
    listLLMModels()
      .then((models) => setLocalModels(models))
      .catch(() => {});
  }, []);

  const persist = (updates: Record<string, unknown>) => {
    updateSingleton("LLMGeneratorSettings", updates).catch(() => {});
  };

  if (loading) {
    return <div className="p-2 small" style={{ color: "#a0a0a8" }}>Loading...</div>;
  }

  return (
    <div className="p-2">
      <h6 style={{ color: "#a0a0a8" }} className="mb-2">LLM Settings</h6>

      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>Provider</Form.Label>
        <Form.Select
          size="sm"
          value={modelService}
          onChange={(e) => {
            setModelService(e.target.value);
            persist({ model_service: e.target.value });
          }}
        >
          <option value="local">Local</option>
          <option value="openrouter">OpenRouter (API)</option>
          <option value="ollama">Ollama</option>
        </Form.Select>
      </Form.Group>

      {isLocal ? (
        <Form.Group className="mb-2">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Model</Form.Label>
          <Form.Select
            size="sm"
            value={modelPath}
            onChange={(e) => {
              setModelPath(e.target.value);
              persist({ model_path: e.target.value });
            }}
          >
            <option value="">Select model...</option>
            {localModels.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </Form.Select>
        </Form.Group>
      ) : (
        <Form.Group className="mb-2">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Model Path</Form.Label>
          <Form.Control
            size="sm"
            value={modelPath}
            onChange={(e) => {
              setModelPath(e.target.value);
              persist({ model_path: e.target.value });
            }}
            placeholder="model-id or endpoint URL"
          />
        </Form.Group>
      )}

      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>
          Temperature ({temperature})
        </Form.Label>
        <Form.Range
          min={0} max={2} step={0.1}
          value={temperature}
          onChange={(e) => {
            const v = Number(e.target.value);
            setTemperature(v);
            persist({ temperature: v });
          }}
        />
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small" style={{ color: "#a0a0a8" }}>Max Tokens</Form.Label>
        <Form.Control
          size="sm" type="number" min={256} max={32768}
          value={maxTokens}
          onChange={(e) => {
            const v = Number(e.target.value);
            setMaxTokens(v);
            persist({ max_new_tokens: v });
          }}
        />
      </Form.Group>

      {precisionOptions.length > 0 && (
        <Form.Group className="mb-2">
          <Form.Label className="small" style={{ color: "#a0a0a8" }}>Runtime Precision</Form.Label>
          <Form.Select
            size="sm"
            value={precision}
            onChange={(e) => {
              setPrecision(e.target.value);
              persist({ dtype: e.target.value });
            }}
          >
            <option value="">Default</option>
            {precisionOptions.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </Form.Select>
        </Form.Group>
      )}
    </div>
  );
}
