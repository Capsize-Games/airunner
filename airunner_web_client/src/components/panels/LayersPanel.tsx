import { useState } from "react";
import Button from "react-bootstrap/Button";

interface LayerInfo {
  id: number;
  name: string;
  visible: boolean;
  selected: boolean;
}

export default function LayersPanel() {
  const [layers, setLayers] = useState<LayerInfo[]>([]);

  const toggleVisibility = (id: number) => {
    setLayers((prev) =>
      prev.map((l) =>
        l.id === id ? { ...l, visible: !l.visible } : l,
      ),
    );
  };

  const selectLayer = (id: number) => {
    setLayers((prev) =>
      prev.map((l) => ({
        ...l,
        selected: l.id === id,
      })),
    );
  };

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">Layers</h6>
        <div className="btn-group btn-group-sm">
          <Button
            variant="outline-secondary"
            size="sm"
            title="Add layer"
          >
            +
          </Button>
          <Button
            variant="outline-secondary"
            size="sm"
            title="Move layer up"
          >
            &#9650;
          </Button>
          <Button
            variant="outline-secondary"
            size="sm"
            title="Move layer down"
          >
            &#9660;
          </Button>
          <Button
            variant="outline-secondary"
            size="sm"
            title="Merge visible"
          >
            &#9878;
          </Button>
          <Button
            variant="outline-secondary"
            size="sm"
            title="Delete layer"
          >
            &#10005;
          </Button>
        </div>
      </div>

      {layers.length === 0 ? (
        <p className="text-muted small">
          No layers yet. Open the canvas and add an image
          to create layers.
        </p>
      ) : (
        <div className="layer-list">
          {layers.map((layer) => (
            <div
              key={layer.id}
              className={`d-flex align-items-center py-1 px-2 mb-1 rounded ${
                layer.selected
                  ? "bg-primary bg-opacity-25"
                  : ""
              }`}
              onClick={() => selectLayer(layer.id)}
              role="button"
            >
              <Button
                variant="link"
                size="sm"
                className={`p-0 me-2 ${
                  layer.visible
                    ? "text-light"
                    : "text-muted"
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleVisibility(layer.id);
                }}
              >
                {layer.visible ? "👁" : "—"}
              </Button>
              <span className="small text-muted flex-grow-1">
                {layer.name}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
