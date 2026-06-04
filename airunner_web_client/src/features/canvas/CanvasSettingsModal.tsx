import { useState, useEffect } from "react";
import Modal from "react-bootstrap/Modal";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";

interface CanvasSettingsModalProps {
  show: boolean;
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  onApply: (width: number, height: number, bgColor: string) => void;
  onHide: () => void;
}

const PRESET_COLORS = [
  { label: "Transparent", value: "transparent" },
  { label: "White",       value: "#ffffff" },
  { label: "Black",       value: "#000000" },
];

export default function CanvasSettingsModal({
  show,
  documentWidth,
  documentHeight,
  documentBgColor,
  onApply,
  onHide,
}: CanvasSettingsModalProps) {
  const [w, setW] = useState(documentWidth);
  const [h, setH] = useState(documentHeight);
  const [bg, setBg] = useState(documentBgColor);
  const [customColor, setCustomColor] = useState(
    PRESET_COLORS.some((p) => p.value === documentBgColor) ? "#808080" : documentBgColor,
  );

  useEffect(() => {
    if (show) {
      setW(documentWidth);
      setH(documentHeight);
      setBg(documentBgColor);
    }
  }, [show, documentWidth, documentHeight, documentBgColor]);

  const isCustom = !PRESET_COLORS.some((p) => p.value === bg);

  return (
    <Modal show={show} onHide={onHide} centered contentClassName="bg-dark text-light border-secondary">
      <Modal.Header closeButton closeVariant="white" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        <Modal.Title style={{ fontSize: 15 }}>Canvas Settings</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form.Group className="mb-3">
          <Form.Label className="small text-secondary">Canvas Size</Form.Label>
          <div className="d-flex gap-2 align-items-center">
            <div className="d-flex align-items-center gap-1">
              <span className="small text-secondary">W</span>
              <Form.Control
                type="number"
                min={8}
                step={8}
                value={w}
                onChange={(e) => setW(Math.max(8, Number(e.target.value)))}
                size="sm"
                style={{ width: 90, background: "#1a1a2e", color: "#ccc", borderColor: "#444" }}
              />
            </div>
            <span className="text-secondary">×</span>
            <div className="d-flex align-items-center gap-1">
              <span className="small text-secondary">H</span>
              <Form.Control
                type="number"
                min={8}
                step={8}
                value={h}
                onChange={(e) => setH(Math.max(8, Number(e.target.value)))}
                size="sm"
                style={{ width: 90, background: "#1a1a2e", color: "#ccc", borderColor: "#444" }}
              />
            </div>
          </div>
        </Form.Group>

        <Form.Group className="mb-1">
          <Form.Label className="small text-secondary">Background</Form.Label>
          <div className="d-flex flex-wrap gap-2">
            {PRESET_COLORS.map((p) => (
              <button
                key={p.value}
                onClick={() => setBg(p.value)}
                title={p.label}
                style={{
                  padding: "3px 10px",
                  borderRadius: 4,
                  border: bg === p.value ? "1.5px solid #6399ff" : "1px solid rgba(255,255,255,0.2)",
                  background: p.value === "transparent"
                    ? "repeating-linear-gradient(45deg,#555 0,#555 4px,#888 4px,#888 8px)"
                    : p.value,
                  color: p.value === "#000000" ? "#fff" : p.value === "transparent" ? "#fff" : "#000",
                  fontSize: 11,
                  cursor: "pointer",
                  minWidth: 80,
                }}
              >
                {p.label}
              </button>
            ))}
            <label style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}>
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 4,
                  background: customColor,
                  border: isCustom ? "1.5px solid #6399ff" : "1px solid rgba(255,255,255,0.2)",
                  cursor: "pointer",
                }}
              />
              <span style={{ fontSize: 11, color: "rgba(255,255,255,0.6)" }}>Custom</span>
              <input
                type="color"
                value={customColor}
                onChange={(e) => { setCustomColor(e.target.value); setBg(e.target.value); }}
                style={{ width: 0, height: 0, opacity: 0, position: "absolute" }}
              />
            </label>
          </div>
        </Form.Group>
      </Modal.Body>
      <Modal.Footer style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        <Button variant="outline-secondary" size="sm" onClick={onHide}>Cancel</Button>
        <Button variant="primary" size="sm" onClick={() => { onApply(w, h, bg); onHide(); }}>Apply</Button>
      </Modal.Footer>
    </Modal>
  );
}
