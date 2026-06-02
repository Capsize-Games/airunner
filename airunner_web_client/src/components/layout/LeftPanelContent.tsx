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
import ProgressBar from "react-bootstrap/ProgressBar";

// ── Knowledge Base ──
export function KnowledgeBasePanel() {
  const [documents, setDocuments] = useState<
    { id: number; name: string; active: boolean; indexed: boolean }[]
  >([]);
  const [indexing, setIndexing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(true);
  const indexedDocs = documents.filter((d) => d.indexed).length;
  const totalDocs = documents.length;

  const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

  const load = useCallback(async () => {
    try {
      const { listKnowledgeBaseDocuments } = await import(
        "../../api/client"
      );
      const data = await listKnowledgeBaseDocuments();
      const docs = (data.documents ?? []).map((d) => ({
        id: d.id,
        name: d.path.split("/").pop() || d.path,
        active: d.active,
        indexed: d.indexed,
      }));
      setDocuments(docs);
    } catch {
      // unavailable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.accept =
      ".txt,.md,.pdf,.epub,.mobi,.html,.htm,.zim,.doc,.docx,.odt";
    input.onchange = () => {
      input.remove();
    };
    input.click();
  };

  const handleIndex = async () => {
    setIndexing(true);
    setProgress(0);
    const id = setInterval(() => {
      setProgress((p) => {
        if (p >= 90) {
          clearInterval(id);
          return p;
        }
        return p + 10;
      });
    }, 500);
    setTimeout(() => {
      clearInterval(id);
      setIndexing(false);
      setProgress(100);
    }, 5000);
  };

  const handleCancel = () => {
    setIndexing(false);
    setProgress(0);
  };

  if (loading) {
    return (
      <div className="p-2">
        <h6 className="text-muted mb-2">Knowledge Base</h6>
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      </div>
    );
  }

  return (
    <div className="d-flex flex-column h-100 p-2">
      <h6 className="text-muted mb-2">Knowledge Base</h6>

      {/* Document table — fills available space */}
      <div className="overflow-auto mb-2" style={{ flex: 1, minHeight: 0 }}>
        {documents.length === 0 ? (
          <p className="text-muted small">No documents loaded.</p>
        ) : (
          <table
            className="table table-sm table-dark mb-0"
            style={{ fontSize: "0.75rem" }}
          >
            <thead>
              <tr>
                <th>Name</th>
                <th style={{ width: 50, textAlign: "center" }}>
                  Active
                </th>
                <th style={{ width: 55, textAlign: "center" }}>
                  Indexed
                </th>
                <th style={{ width: 45, textAlign: "center" }}>
                  Error
                </th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td
                    className="text-truncate"
                    style={{ maxWidth: 180 }}
                    title={doc.name}
                  >
                    {doc.name}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    {doc.active ? "✅" : "—"}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    {doc.indexed ? "✅" : "—"}
                  </td>
                  <td style={{ textAlign: "center" }}>—</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Statistics */}
      <div className="row g-2 mb-1 flex-shrink-0">
        <div className="col-4">
          <div className="stat-box">
            <span className="stat-label">Total</span>
            <span className="stat-value">{totalDocs}</span>
          </div>
        </div>
        <div className="col-4">
          <div className="stat-box">
            <span className="stat-label">Indexed</span>
            <span className="stat-value text-success">
              {indexedDocs}
            </span>
          </div>
        </div>
        <div className="col-4">
          <div className="stat-box">
            <span className="stat-label">Pending</span>
            <span className="stat-value text-warning">
              {totalDocs - indexedDocs}
            </span>
          </div>
        </div>
      </div>

      {/* Progress bar + toolbar */}
      <div className="d-flex align-items-center gap-1 flex-shrink-0">
        <div className="flex-grow-1">
          <ProgressBar
            now={indexing ? progress : 0}
            animated={indexing}
            variant={indexing ? "info" : "secondary"}
            style={{ height: 6 }}
          />
        </div>
        <button
          title="Import document(s) into knowledge base"
          onClick={handleImport}
          style={{
            background: "transparent",
            border: "1px solid #444",
            borderRadius: 4,
            width: 30,
            height: 30,
            padding: 4,
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          <img
            src={icon("upload")}
            alt="Import"
            style={{ width: 16, height: 16, filter: "invert(0.7)" }}
          />
        </button>
        {indexing ? (
          <button
            title="Cancel indexing"
            onClick={handleCancel}
            style={{
              background: "transparent",
              border: "1px solid #444",
              borderRadius: 4,
              width: 30,
              height: 30,
              padding: 4,
              cursor: "pointer",
              flexShrink: 0,
            }}
          >
            <img
              src={icon("circle-x")}
              alt="Cancel"
              style={{ width: 16, height: 16, filter: "invert(0.7)" }}
            />
          </button>
        ) : (
          <button
            title="Index all documents"
            onClick={handleIndex}
            style={{
              background: "transparent",
              border: "1px solid #444",
              borderRadius: 4,
              width: 30,
              height: 30,
              padding: 4,
              cursor: "pointer",
              flexShrink: 0,
            }}
          >
            <img
              src={icon("database")}
              alt="Index"
              style={{ width: 16, height: 16, filter: "invert(0.7)" }}
            />
          </button>
        )}
      </div>
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
