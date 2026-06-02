import { useState, useEffect, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
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