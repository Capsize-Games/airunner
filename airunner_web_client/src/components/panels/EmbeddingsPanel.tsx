import { useState, useEffect, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import Form from "react-bootstrap/Form";
import type { EmbeddingInfo } from "../../api/client";

export default function EmbeddingsPanel() {
  const [search, setSearch] = useState("");
  const [embeddings, setEmbeddings] = useState<EmbeddingInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const scan = useCallback(async () => {
    setLoading(true);
    try {
      const { listEmbeddings } = await import("../../api/client");
      const data = await listEmbeddings();
      setEmbeddings(data.embeddings);
    } catch {
      setEmbeddings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    scan();
  }, [scan]);

  const filtered = embeddings.filter((e) =>
    e.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">Embeddings</h6>
        <button
          className="btn btn-outline-secondary btn-sm"
          onClick={scan}
          disabled={loading}
        >
          Scan
        </button>
      </div>

      <Form.Control
        size="sm"
        type="search"
        placeholder="Filter embeddings..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="bg-dark text-light border-secondary mb-2"
      />

      {loading ? (
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      ) : filtered.length === 0 ? (
        <p className="text-muted small">
          {embeddings.length === 0
            ? "No textual inversion embeddings found. Add embedding files to your models directory and click Scan."
            : "No embeddings match your filter."}
        </p>
      ) : (
        <div className="embed-list">
          {filtered.map((e) => (
            <div key={e.path} className="small text-muted py-1">
              {e.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
