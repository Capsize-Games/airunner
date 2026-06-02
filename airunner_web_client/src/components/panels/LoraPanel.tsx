import { useState } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";

export default function LoraPanel() {
  const [search, setSearch] = useState("");
  const [loras, setLoras] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // TODO: fetch LoRA list from /api/v1/catalog/resources/Lora/query
  // For now, show placeholder data sourced from the services catalog.

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">LoRA</h6>
        <Button
          size="sm"
          variant="outline-secondary"
          onClick={() => setLoras([])}
        >
          Scan
        </Button>
      </div>

      <Form.Control
        size="sm"
        type="search"
        placeholder="Filter LoRA..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="bg-dark text-light border-secondary mb-2"
      />

      {loading ? (
        <p className="text-muted small">Loading...</p>
      ) : loras.length === 0 ? (
        <p className="text-muted small">
          No LoRA models found. Add .safetensors files to
          your models directory and click Scan.
        </p>
      ) : (
        <div className="lora-list">
          {loras
            .filter((l) =>
              l.toLowerCase().includes(search.toLowerCase()),
            )
            .map((l) => (
              <div key={l} className="small text-muted py-1">
                {l}
              </div>
            ))}
        </div>
      )}

      <Button
        size="sm"
        variant="primary"
        className="w-100 mt-2"
        disabled={loras.length === 0}
      >
        Apply LoRA
      </Button>
    </div>
  );
}
