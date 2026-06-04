import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";

/** Load a bool from localStorage. */
function loadBool(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key);
    return v !== null ? v === "true" : fallback;
  } catch { return fallback; }
}
/** Load a number from localStorage. */
function loadNum(key: string, fallback: number): number {
  try {
    const v = localStorage.getItem(key);
    return v !== null ? Number(v) : fallback;
  } catch { return fallback; }
}
function persist(key: string, val: unknown) {
  try { localStorage.setItem(key, String(val)); } catch { /* */ }
}

export default function GridPanel() {
  const [showGrid, setShowGrid] = useState(() =>
    loadBool("airunner_grid_show", true),
  );
  const [snapToGrid, setSnapToGrid] = useState(() =>
    loadBool("airunner_grid_snap", true),
  );
  const [cellSize, setCellSize] = useState(() =>
    loadNum("airunner_grid_cell", 64),
  );
  const [lineWidth, setLineWidth] = useState(() =>
    loadNum("airunner_grid_line_w", 1),
  );

  return (
    <div className="p-2">
      <h6 className="text-muted mb-2">Grid Settings</h6>

      <Form.Group className="mb-2">
        <Form.Check
          type="switch"
          label="Show Grid"
          checked={showGrid}
          onChange={(e) => {
            setShowGrid(e.target.checked);
            persist("airunner_grid_show", e.target.checked);
          }}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Check
          type="switch"
          label="Snap to Grid"
          checked={snapToGrid}
          onChange={(e) => {
            setSnapToGrid(e.target.checked);
            persist("airunner_grid_snap", e.target.checked);
          }}
          className="small"
        />
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small">Cell Size</Form.Label>
        <Form.Control
          size="sm"
          type="number"
          min={1}
          max={512}
          value={cellSize}
          onChange={(e) => {
            const v = Number(e.target.value);
            setCellSize(v);
            persist("airunner_grid_cell", v);
          }}
        />
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small">Line Width</Form.Label>
        <Form.Range
          min={1}
          max={10}
          value={lineWidth}
          onChange={(e) => {
            const v = Number(e.target.value);
            setLineWidth(v);
            persist("airunner_grid_line_w", v);
          }}
        />
        <small>{lineWidth}px</small>
      </Form.Group>
    </div>
  );
}
