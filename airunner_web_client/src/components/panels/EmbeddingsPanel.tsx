import { useState } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";

export default function EmbeddingsPanel() {
  const [search, setSearch] = useState("");
  const [embeddings, setEmbeddings] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // TODO: fetch embeddings from /api/v1/catalog/resources/Embeddings/query

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">Embeddings</h6>
        <Button
          size="sm"
          variant="outline-secondary"
          onClick={() => setEmbeddings([])}
        >
          Scan
        </Button>
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
        <p className="text-muted small">Loading...</p>
      ) : embeddings.length === 0 ? (
        <p className="text-muted small">
          No textual inversion embeddings found. Add
          embedding files to your models directory and click
          Scan.
        </p>
      ) : (
        <div className="embed-list">
          {embeddings
            .filter((e) =>
              e.toLowerCase().includes(search.toLowerCase()),
            )
            .map((e) => (
              <div key={e} className="small text-muted py-1">
                {e}
              </div>
            ))}
        </div>
      )}

      <Button
        size="sm"
        variant="primary"
        className="w-100 mt-2"
        disabled={embeddings.length === 0}
      >
        Apply Embeddings
      </Button>
    </div>
  );
}
