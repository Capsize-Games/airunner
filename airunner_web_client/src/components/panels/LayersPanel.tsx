import { useState, useEffect, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import type { LayerInfo } from "../../api/client";

export default function LayersPanel() {
  const [layers, setLayers] = useState<LayerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const reload = useCallback(async () => {
    try {
      const { listLayers } = await import("../../api/client");
      const data = await listLayers();
      setLayers(data.layers);
    } catch {
      // unavailable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const handleAdd = async () => {
    try {
      const { createLayer } = await import("../../api/client");
      const layer = await createLayer();
      setLayers((prev) => [...prev, layer]);
      setSelectedId(layer.id);
    } catch { /* */ }
  };

  const handleDelete = async (id: number) => {
    try {
      const { deleteLayer } = await import("../../api/client");
      await deleteLayer(id);
      setLayers((prev) => prev.filter((l) => l.id !== id));
      if (selectedId === id) setSelectedId(null);
    } catch { /* */ }
  };

  const handleMove = async (id: number, direction: "up" | "down") => {
    try {
      const { moveLayer } = await import("../../api/client");
      await moveLayer(id, direction);
      await reload();
    } catch { /* */ }
  };

  const handleMergeVisible = async () => {
    try {
      const { mergeVisibleLayers } = await import("../../api/client");
      await mergeVisibleLayers();
      await reload();
    } catch { /* */ }
  };

  const toggleVisibility = async (id: number) => {
    const layer = layers.find((l) => l.id === id);
    if (!layer) return;
    try {
      const { updateLayer } = await import("../../api/client");
      const updated = await updateLayer(id, { visible: !layer.visible });
      setLayers((prev) =>
        prev.map((l) => (l.id === id ? updated : l)),
      );
    } catch { /* */ }
  };

  const selectLayer = (id: number) => {
    setSelectedId(id);
  };

  if (loading) {
    return (
      <div className="p-2">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h6 className="text-muted mb-0">Layers</h6>
        </div>
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      </div>
    );
  }

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">Layers</h6>
        <div className="btn-group btn-group-sm">
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={handleAdd}
            title="Add layer"
          >
            +
          </button>
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => selectedId && handleMove(selectedId, "up")}
            disabled={!selectedId}
            title="Move layer up"
          >
            &#9650;
          </button>
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => selectedId && handleMove(selectedId, "down")}
            disabled={!selectedId}
            title="Move layer down"
          >
            &#9660;
          </button>
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={handleMergeVisible}
            disabled={layers.filter((l) => l.visible).length < 2}
            title="Merge visible"
          >
            &#9878;
          </button>
          <button
            className="btn btn-outline-secondary btn-sm"
            onClick={() => selectedId && handleDelete(selectedId)}
            disabled={!selectedId}
            title="Delete layer"
          >
            &#10005;
          </button>
        </div>
      </div>

      {layers.length === 0 ? (
        <p className="text-muted small">
          No layers yet. Click + to create one.
        </p>
      ) : (
        <div className="layer-list">
          {layers.map((layer) => (
            <div
              key={layer.id}
              className={`d-flex align-items-center py-1 px-2 mb-1 rounded ${
                layer.id === selectedId
                  ? "bg-primary bg-opacity-25"
                  : ""
              }`}
              onClick={() => selectLayer(layer.id)}
              role="button"
            >
              <button
                className="btn btn-link btn-sm p-0 me-2"
                style={{
                  color: layer.visible ? "#c8c8c8" : "#666",
                  textDecoration: "none",
                  border: "none",
                  background: "transparent",
                  lineHeight: 1,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleVisibility(layer.id);
                }}
                title={layer.visible ? "Hide" : "Show"}
              >
                {layer.visible ? "👁" : "—"}
              </button>
              <span className="small text-muted flex-grow-1">
                {layer.name}
              </span>
              {layer.locked && (
                <span className="small text-muted me-1" title="Locked">
                  🔒
                </span>
              )}
              {layer.opacity < 100 && (
                <span className="small text-muted">{layer.opacity}%</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
