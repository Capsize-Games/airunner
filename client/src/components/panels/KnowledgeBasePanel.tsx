import { useEffect, useRef } from "react";
import ProgressBar from "react-bootstrap/ProgressBar";
import KBRow from "./knowledge-base/KBRow";
import LucideIcon from "../shared/LucideIcon";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_DOCUMENTS, EVENT_INDEX_PROGRESS } from "../../features/events/types";
import { useKnowledgeBaseDocs } from "../../hooks/useKnowledgeBaseDocs";
import { useLocalStorage } from "../../hooks/useLocalStorage";

export function KnowledgeBasePanel() {
  const { docs, loading, reload, toggle } = useKnowledgeBaseDocs();
  const [indexing, setIndexing] = useLocalStorage("kb_indexing", false);
  const [modelLoading, setModelLoading] = useLocalStorage("kb_model_loading", false);
  const [progress, setProgress] = useLocalStorage("kb_progress", 0);

  const documents = docs.map((d) => ({
    id: d.id,
    name: d.path.split("/").pop() || d.path,
    active: d.active,
    indexed: d.indexed,
  }));

  // Recover state when panel remounts mid-indexing (e.g. panel was
  // closed and reopened, or browser was reloaded).  If the document
  // list has loaded and every document is already indexed, indexing
  // completed while the panel was unmounted — clear the progress.
  const recoveredRef = useRef(false);
  useEffect(() => {
    if (!indexing || loading || recoveredRef.current) return;
    recoveredRef.current = true;
    setModelLoading(false);
    if (documents.length > 0 && documents.every((d) => d.indexed)) {
      setIndexing(false);
      setProgress(0);
    }
  }, [indexing, loading, documents, setIndexing, setModelLoading, setProgress]);

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
      const { indexAllDocuments } = await import("../../api/client");
      await indexAllDocuments(true);
    } catch {
      setIndexing(false);
      setModelLoading(false);
    }
  };

  const handleCancel = async () => {
    setIndexing(false);
    setProgress(0);
    try {
      const { cancelIndexing } = await import("../../api/client");
      await cancelIndexing();
    } catch { /* */ }
  };

  const indexedDocs = documents.filter((d) => d.indexed).length;
  const totalDocs = documents.length;
  const activeDocs = documents.filter((d) => d.active).length;

  return (
    <div className="d-flex flex-column h-100">
      {/* Sticky header */}
      <div
        className="flex-shrink-0 bg-theme-panel border-b-theme"
        style={{ padding: "8px 12px 6px" }}
      >
        <span className="text-panel-label text-uppercase">
          Knowledge Base
        </span>
      </div>

      {/* Scrollable content */}
      <div className="scroll-panel">
        {loading ? (
          <div className="p-3 text-center">
            <div className="spinner-border spinner-border-sm" role="status" />
          </div>
        ) : documents.length === 0 ? (
          <p className="text-muted small p-2">No documents loaded.</p>
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

      {/* Sticky footer — stats + progress + buttons */}
      <div
        className="flex-shrink-0 border-t-theme bg-theme-panel d-flex flex-column"
        style={{ padding: "6px 10px 8px", gap: 6 }}
      >
        {/* Stats row */}
        <div className="row g-2">
          {[
            { label: "Total",   value: totalDocs,              color: undefined },
            { label: "Active",  value: activeDocs,             color: "var(--bs-info)" },
            { label: "Indexed", value: indexedDocs,            color: "var(--bs-success)" },
            { label: "Pending", value: totalDocs - indexedDocs, color: "var(--bs-warning)" },
          ].map(({ label, value, color }) => (
            <div key={label} className="col-3">
              <div className="stat-box">
                <span className="stat-label">{label}</span>
                <span className="stat-value" style={color ? { color } : undefined}>{value}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Progress + action buttons */}
        <div className="d-flex align-items-center gap-1">
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
            className="icon-btn icon-btn-bordered"
            title="Import document(s) into knowledge base"
            onClick={handleImport}
          >
            <LucideIcon name="upload" size={16} />
          </button>
          {indexing ? (
            <button
              className="icon-btn icon-btn-bordered"
              title="Cancel indexing"
              onClick={handleCancel}
            >
              <LucideIcon name="circle-x" size={16} />
            </button>
          ) : (
            <button
              className="icon-btn icon-btn-bordered"
              title="Index all documents"
              onClick={handleIndex}
            >
              <LucideIcon name="database" size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
