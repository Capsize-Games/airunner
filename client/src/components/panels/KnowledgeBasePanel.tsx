import { useState } from "react";
import Spinner from "react-bootstrap/Spinner";
import ProgressBar from "react-bootstrap/ProgressBar";
import { BASE_URL } from "../../types/api";
import KBRow from "./knowledge-base/KBRow";
import LucideIcon from "../shared/LucideIcon";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_DOCUMENTS, EVENT_INDEX_PROGRESS } from "../../features/events/types";
import { useKnowledgeBaseDocs } from "../../hooks/useKnowledgeBaseDocs";

// ── Knowledge Base ──
export function KnowledgeBasePanel() {
  const { docs, loading, reload, toggle } = useKnowledgeBaseDocs();
  const [indexing, setIndexing] = useState(false);
  const [modelLoading, setModelLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const documents = docs.map((d) => ({
    id: d.id,
    name: d.path.split("/").pop() || d.path,
    active: d.active,
    indexed: d.indexed,
  }));

  useEventBus([EVENT_DOCUMENTS], (_event, data) => {
    const payload = data as { type?: string };
    if (payload.type === "reload") reload();
  });

  useEventBus([EVENT_INDEX_PROGRESS], (_event, data) => {
    const payload = data as {
      type?: string;
      current?: number;
      total?: number;
    };
    if (payload.type === "progress") {
      setModelLoading(false);
      const total = Number(payload.total) || 1;
      const current = Number(payload.current) || 0;
      setProgress(Math.round((current / total) * 100));
    } else if (payload.type === "complete") {
      setProgress(100);
      setModelLoading(false);
      setTimeout(() => {
        setIndexing(false);
        setProgress(0);
        reload();
      }, 500);
    } else if (payload.type === "error") {
      setModelLoading(false);
      setIndexing(false);
      setProgress(0);
    }
  });

  const handleToggle = async (docId: number) => {
    await toggle(docId);
    window.dispatchEvent(new Event("knowledge-base-changed"));
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
    input.onchange = () => { input.remove(); };
    input.click();
  };

  const handleIndex = async () => {
    setIndexing(true);
    setModelLoading(true);
    setProgress(0);
    await new Promise((r) => setTimeout(r, 0));
    try {
      await fetch(`${BASE_URL}/api/v1/knowledge-base/documents/index-all`, {
        method: "POST",
      });
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
                <th style={{ width: 50, textAlign: "center" }}>Active</th>
                <th style={{ width: 55, textAlign: "center" }}>Indexed</th>
                <th style={{ width: 45, textAlign: "center" }}>Error</th>
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
        <div className="flex-grow-1" style={{ position: "relative", height: 6 }}>
          {modelLoading ? (
            <div
              style={{
                height: 6,
                borderRadius: 4,
                background: "linear-gradient(90deg, transparent 0%, #0dcaf0 50%, transparent 100%)",
                backgroundSize: "200% 100%",
                animation: "indeterminate-bar 1.5s ease-in-out infinite",
              }}
            />
          ) : (
            <ProgressBar
              now={indexing ? progress : 0}
              animated={indexing}
              variant={indexing ? "info" : "secondary"}
              style={{ height: 6 }}
            />
          )}
        </div>
        <button
          title="Import document(s) into knowledge base"
          onClick={handleImport}
          style={{
            background: "transparent", border: "1px solid #444",
            borderRadius: 4, width: 30, height: 30, padding: 4,
            cursor: "pointer", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
        >
          <LucideIcon name="upload" size={16} />
        </button>
        {indexing ? (
          <button
            title="Cancel indexing"
            onClick={handleCancel}
            style={{
              background: "transparent", border: "1px solid #444",
              borderRadius: 4, width: 30, height: 30, padding: 4,
              cursor: "pointer", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <LucideIcon name="circle-x" size={16} />
          </button>
        ) : (
          <button
            title="Index all documents"
            onClick={handleIndex}
            style={{
              background: "transparent", border: "1px solid #444",
              borderRadius: 4, width: 30, height: 30, padding: 4,
              cursor: "pointer", flexShrink: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <LucideIcon name="database" size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
