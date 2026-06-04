import Form from "react-bootstrap/Form";
import type { FilterConfig, CanvasLayer } from "./useCanvasState";

interface FilterPanelProps {
  layer: CanvasLayer | null;
  onSetFilters: (id: string, filters: FilterConfig[]) => void;
}

const FILTER_DEFS: {
  type: FilterConfig["type"];
  label: string;
  param: string;
  min: number;
  max: number;
  step: number;
}[] = [
  { type: "blur", label: "Blur", param: "blurRadius", min: 0, max: 40, step: 1 },
  { type: "pixelate", label: "Pixelate", param: "pixelSize", min: 1, max: 20, step: 1 },
  { type: "noise", label: "Noise", param: "noise", min: 0, max: 1, step: 0.01 },
  { type: "brighten", label: "Brighten", param: "brightness", min: -1, max: 1, step: 0.01 },
  { type: "contrast", label: "Contrast", param: "contrast", min: -100, max: 100, step: 1 },
];

const GRAYSCALE: FilterConfig["type"] = "grayscale";

export default function FilterPanel({
  layer,
  onSetFilters,
}: FilterPanelProps) {
  if (!layer) {
    return (
      <div className="p-2">
        <small className="text-muted">
          Select a layer to edit filters.
        </small>
      </div>
    );
  }

  const currentFilters = layer.filters;
  const hasGrayscale = currentFilters.some(
    (f) => f.type === GRAYSCALE,
  );

  const updateFilter = (
    type: FilterConfig["type"],
    param: string,
    value: number,
  ) => {
    const existing = currentFilters.findIndex((f) => f.type === type);
    let next: FilterConfig[];
    if (existing >= 0) {
      next = currentFilters.map((f, i) =>
        i === existing
          ? { ...f, params: { ...f.params, [param]: value } }
          : f,
      );
    } else {
      next = [
        ...currentFilters,
        { type, params: { [param]: value } },
      ];
    }
    onSetFilters(layer.id, next);
  };

  const removeFilter = (type: FilterConfig["type"]) => {
    onSetFilters(
      layer.id,
      currentFilters.filter((f) => f.type !== type),
    );
  };

  const toggleGrayscale = () => {
    if (hasGrayscale) {
      removeFilter(GRAYSCALE);
    } else {
      onSetFilters(layer.id, [
        ...currentFilters,
        { type: GRAYSCALE, params: {} },
      ]);
    }
  };

  const getParam = (type: FilterConfig["type"], param: string): number => {
    const f = currentFilters.find((x) => x.type === type);
    return f?.params[param] ?? 0;
  };

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Filters</h6>

      {FILTER_DEFS.map((def) => {
        const val = getParam(def.type, def.param);
        const isActive = currentFilters.some(
          (f) => f.type === def.type,
        );
        return (
          <Form.Group key={def.type} className="mb-2">
            <div className="d-flex justify-content-between align-items-center">
              <Form.Label className="small mb-0">
                {def.label}
              </Form.Label>
              <button
                className="btn btn-link btn-sm p-0 text-danger"
                onClick={() => removeFilter(def.type)}
                disabled={!isActive}
                title={`Remove ${def.label}`}
                style={{
                  textDecoration: "none",
                  lineHeight: 1,
                  opacity: isActive ? 1 : 0.3,
                }}
              >
                ✕
              </button>
            </div>
            <Form.Range
              min={def.min}
              max={def.max}
              step={def.step}
              value={isActive ? val : def.min}
              onChange={(e) =>
                updateFilter(
                  def.type,
                  def.param,
                  Number(e.target.value),
                )
              }
            />
            <small className="text-muted">
              {isActive ? val.toFixed(2) : "Off"}
            </small>
          </Form.Group>
        );
      })}

      <Form.Check
        type="switch"
        id="filter-grayscale"
        label="Grayscale"
        checked={hasGrayscale}
        onChange={toggleGrayscale}
        className="small"
      />
    </div>
  );
}
