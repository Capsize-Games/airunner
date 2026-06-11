import { useState, useEffect } from "react";
import Modal from "react-bootstrap/Modal";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";

const PRESET_COLORS = [
  { label: "Transparent", value: "transparent" },
  { label: "White",       value: "#ffffff" },
  { label: "Black",       value: "#000000" },
];

interface NewLayerModalProps {
  show: boolean;
  onConfirm: (name: string, opacity: number, fillColor: string) => void;
  onHide: () => void;
  layerIndex: number;
  defaultName: string;
}

export default function NewLayerModal({
  show,
  onConfirm,
  onHide,
  defaultName,
}: NewLayerModalProps) {
  const [name, setName] = useState(defaultName);

  useEffect(() => {
    if (show) setName(defaultName);
  }, [show, defaultName]);
  const [opacity, setOpacity] = useState(1);
  const [fillColor, setFillColor] = useState("transparent");

  return (
    <Modal
      show={show}
      onHide={onHide}
      centered
      size="sm"
      contentClassName="bg-dark"
      style={{ color: "var(--theme-text)" }}
    >
      <Modal.Header
        closeButton
        closeVariant="white"
        style={{ borderColor: "var(--theme-border)" }}
      >
        <Modal.Title style={{ fontSize: 15, color: "var(--theme-heading)" }}>
          New Layer
        </Modal.Title>
      </Modal.Header>
      <Modal.Body style={{ color: "var(--theme-text)" }}>
        <Form.Group className="mb-2">
          <Form.Label className="text-theme-secondary" style={{ fontSize: 12 }}>
            Name
          </Form.Label>
          <Form.Control
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            size="sm"
            style={{
              background: "var(--theme-input-bg)",
              color: "var(--theme-text)",
              borderColor: "var(--theme-input-border)",
            }}
          />
        </Form.Group>
        <Form.Group className="mb-2">
          <Form.Label className="text-theme-secondary" style={{ fontSize: 12 }}>
            Opacity
          </Form.Label>
          <div className="d-flex align-items-center gap-2">
            <Form.Range
              min={0} max={1} step={0.01}
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="flex-grow-1"
            />
            <span style={{ fontSize: 11, fontFamily: "monospace", color: "rgba(255,255,255,0.5)", width: 32, textAlign: "right" }}>
              {Math.round(opacity * 100)}%
            </span>
          </div>
        </Form.Group>
        <Form.Group className="mb-1">
          <Form.Label className="text-theme-secondary" style={{ fontSize: 12 }}>
            Fill Color
          </Form.Label>
          <div className="d-flex flex-wrap gap-2">
            {PRESET_COLORS.map((p) => (
              <button
                key={p.value}
                onClick={() => setFillColor(p.value)}
                title={p.label}
                style={{
                  padding: "3px 10px",
                  borderRadius: 4,
                  border: fillColor === p.value
                    ? "1.5px solid #6399ff"
                    : "1px solid var(--theme-border)",
                  background: p.value === "transparent"
                    ? "repeating-linear-gradient(45deg,#555 0,#555 4px,#888 4px,#888 8px)"
                    : p.value,
                  color: p.value === "#000000" ? "#fff"
                    : p.value === "transparent" ? "#fff"
                    : "var(--theme-text)",
                  fontSize: 11,
                  cursor: "pointer",
                  minWidth: 80,
                  transition: "border-color 0.1s, opacity 0.1s",
                }}
                onMouseEnter={(e) => {
                  if (fillColor !== p.value)
                    e.currentTarget.style.borderColor = "rgba(99,153,255,0.5)";
                }}
                onMouseLeave={(e) => {
                  if (fillColor !== p.value)
                    e.currentTarget.style.borderColor = "var(--theme-border)";
                }}
              >
                {p.label}
              </button>
            ))}
            <label className="d-flex align-items-center" style={{ gap: 4, cursor: "pointer" }}>
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 4,
                  background: fillColor === "transparent" ? "#808080" : fillColor,
                  border: !PRESET_COLORS.some((p) => p.value === fillColor)
                    ? "1.5px solid #6399ff"
                    : "1px solid var(--theme-border)",
                  cursor: "pointer",
                }}
              />
              <span className="text-section-label">
                Custom
              </span>
              <input
                type="color"
                value={fillColor === "transparent" ? "#808080" : fillColor}
                onChange={(e) => setFillColor(e.target.value)}
                style={{ width: 0, height: 0, opacity: 0, position: "absolute" }}
              />
            </label>
          </div>
        </Form.Group>
      </Modal.Body>
      <Modal.Footer style={{ borderColor: "var(--theme-border)" }}>
        <Button variant="outline-secondary" size="sm" onClick={onHide}>Cancel</Button>
        <Button variant="primary" size="sm" onClick={() => { onConfirm(name, opacity, fillColor); onHide(); }}>
          Add Layer
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
