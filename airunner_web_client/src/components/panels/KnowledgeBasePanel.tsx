import { useState, useEffect, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import ProgressBar from "react-bootstrap/ProgressBar";
import { BASE_URL } from "../../types/api";
import KBRow from "./knowledge-base/KBRow";

// ── Knowledge Base ──
export function KnowledgeBasePanel() {
  const [documents, setDocuments] = useState<
    { id: number; name: string; active: boolean; indexed: boolean }[]
  >([]);
  const [indexing, setIndexing] = useState(false);
  const [modelLoading, setModelLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(true);

  const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

  const reload = useCallback(async () => {
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
    reload();
  }, [reload]);

  useEffect(() => {
    const handler = () => reload();
    window.addEventListener("knowledge-base-changed", handler);
    return () =>
      window.removeEventListener("knowledge-base-changed", handler);
  }, [reload]);

  useEffect(() => {
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/knowledge-base/documents/watch`,
    );
    eventSource.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "reload") {
          reload();
        }
      } catch { /* ignore malformed events */ }
    });
    eventSource.onerror = () => {
      // The browser will automatically reconnect EventSource on error
    };
    return () => {
      eventSource.close();
    };
  }, [reload]);

  const handleToggle = async (docId: number) => {
    try {
      const { toggleDocumentActive } = await import(
        "../../api/client"
      );
      const result = await toggleDocumentActive(docId);
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === docId ? { ...d, active: result.active } : d,
        ),
      );
      window.dispatchEvent(new Event("knowledge-base-changed"));
    } catch {
      // unchanged
    }
  };

  const handleDragStart = (
    e: React.DragEvent<HTMLTableRowElement>,
    docId: number,
  ) => {
    e.dataTransfer.setData("application/x-airunner-doc-id", String(docId));
    e.dataTransfer.effectAllowed = "copy";
  };

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

  // Subscribe to indexing progress SSE
  useEffect(() => {
    if (!indexing) return;
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/knowledge-base/documents/index-progress`,
    );
    let progressStarted = false;
    eventSource.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "progress") {
          if (!progressStarted) {
            progressStarted = true;
            setModelLoading(false);
          }
          const total = Number(data.total) || 1;
          const current = Number(data.current) || 0;
          setProgress(Math.round((current / total) * 100));
        } else if (data.type === "complete") {
          setProgress(100);
          setModelLoading(false);
          eventSource.close();
          // Brief pause so the user sees 100% before resetting
          setTimeout(() => {
            setIndexing(false);
            setProgress(0);
            reload();
          }, 500);
        } else if (data.type === "error") {
          setModelLoading(false);
          setIndexing(false);
          setProgress(0);
          eventSource.close();
        }
      } catch { /* ignore */ }
    });
    eventSource.onerror = () => {
      // EventSource auto-reconnects on error
    };
    return () => {
      eventSource.close();
    };
  }, [indexing, reload]);

  const handleIndex = async () => {
    setIndexing(true);
    setModelLoading(true);
    setProgress(0);
    try {
      await fetch(
        `${BASE_URL}/api/v1/knowledge-base/documents/index-all`,
        { method: "POST" },
      );
    } catch {
      setIndexing(false);
      setModelLoading(false);
    }
  };

  const handleCancel = async () => {
    setIndexing(false);
    setProgress(0);
    try {
      await fetch(
        `${BASE_URL}/api/v1/knowledge-base/documents/index-cancel`,
        { method: "POST" },
      );
    } catch { /* */ }
  };

  const indexedDocs = documents.filter((d) => d.indexed).length;
  const totalDocs = documents.length;
  const activeDocs = documents.filter((d) => d.active).length;

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
                <KBRow
                  key={doc.id}
                  doc={doc}
                  onToggle={handleToggle}
                  onDragStart={handleDragStart}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="row g-2 mb-1 flex-shrink-0">
        <div className="col-3">
          <div className="stat-box">
            <span className="stat-label">Total</span>
            <span className="stat-value">{totalDocs}</span>
          </div>
        </div>
        <div className="col-3">
          <div className="stat-box">
            <span className="stat-label">Active</span>
            <span className="stat-value text-info">{activeDocs}</span>
          </div>
        </div>
        <div className="col-3">
          <div className="stat-box">
            <span className="stat-label">Indexed</span>
            <span className="stat-value text-success">{indexedDocs}</span>
          </div>
        </div>
        <div className="col-3">
          <div className="stat-box">
            <span className="stat-label">Pending</span>
            <span className="stat-value text-warning">
              {totalDocs - indexedDocs}
            </span>
          </div>
        </div>
      </div>

      <div className="d-flex align-items-center gap-1 flex-shrink-0">
        <div className="flex-grow-1">
          <ProgressBar
            now={modelLoading ? 0 : indexing ? progress : 0}
            animated={modelLoading || indexing}
            variant={modelLoading ? "info" : indexing ? "info" : "secondary"}
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
