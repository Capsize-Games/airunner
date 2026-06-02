import { useState, useEffect, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import Form from "react-bootstrap/Form";
import type { LoraInfo } from "../../api/client";

export default function LoraPanel() {
  const [search, setSearch] = useState("");
  const [loras, setLoras] = useState<LoraInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const scan = useCallback(async () => {
    setLoading(true);
    try {
      const { listLoras } = await import("../../api/client");
      const data = await listLoras();
      setLoras(data.loras);
    } catch {
      setLoras([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    scan();
  }, [scan]);

  const filtered = loras.filter((l) =>
    l.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">LoRA</h6>
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
        placeholder="Filter LoRA..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="bg-dark text-light border-secondary mb-2"
      />

      {loading ? (
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      ) : filtered.length === 0 ? (
        <p className="text-muted small">
          {loras.length === 0
            ? "No LoRA models found. Add .safetensors files to your models directory and click Scan."
            : "No LoRA models match your filter."}
        </p>
      ) : (
        <div className="lora-list">
          {filtered.map((l) => (
            <div key={l.path} className="small text-muted py-1">
              {l.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
