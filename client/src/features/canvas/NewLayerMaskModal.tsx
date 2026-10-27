import { useState } from "react";
import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";

type MaskFill = "white" | "black";

interface Props {
  show: boolean;
  layerName: string;
  onAdd: (fill: MaskFill, invert: boolean) => void;
  onHide: () => void;
}

const INIT_OPTIONS: { value: MaskFill | "alpha" | "transfer-alpha" | "grayscale"; label: string }[] = [
  { value: "white",         label: "White (full opacity)" },
  { value: "black",         label: "Black (full transparency)" },
  { value: "alpha",         label: "Layer's alpha channel" },
  { value: "transfer-alpha",label: "Transfer layer's alpha channel" },
  { value: "grayscale",     label: "Grayscale copy of layer" },
];

const radioStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 7,
  marginBottom: 5,
  fontSize: 12,
  color: "rgba(255,255,255,0.8)",
  cursor: "pointer",
};

const labelStyle: React.CSSProperties = {
  fontFamily: "monospace",
  fontSize: 11,
  color: "rgba(255,255,255,0.45)",
  marginBottom: 2,
  display: "block",
};

export default function NewLayerMaskModal({ show, layerName, onAdd, onHide }: Props) {
  const [init, setInit] = useState<string>("white");
  const [invert, setInvert] = useState(false);

  const handleAdd = () => {
    const fill: MaskFill = init === "black" ? "black" : "white";
    onAdd(fill, invert);
    setInit("white");
    setInvert(false);
  };

  const panelStyle: React.CSSProperties = {
    background: "#1e1e2e",
    border: "none",
  };

  return (
    <Modal show={show} onHide={onHide} size="sm" centered dialogClassName="layer-mask-modal">
      <Modal.Header closeButton style={{ ...panelStyle, borderBottom: "1px solid rgba(255,255,255,0.1)", padding: "10px 16px" }}>
        <Modal.Title style={{ fontSize: 13, fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>
          Add Layer Mask
        </Modal.Title>
      </Modal.Header>
      <Modal.Body style={{ ...panelStyle, padding: "14px 16px" }}>
        <div style={{ marginBottom: 10 }}>
          <span style={labelStyle}>Layer: {layerName}</span>
        </div>
        <div style={{ marginBottom: 10 }}>
          <span style={{ ...labelStyle, marginBottom: 8 }}>Initialize Layer Mask to:</span>
          {INIT_OPTIONS.map((opt) => (
            <label key={opt.value} style={radioStyle}>
              <input
                type="radio"
                name="maskInit"
                value={opt.value}
                checked={init === opt.value}
                onChange={() => setInit(opt.value)}
                style={{ accentColor: "var(--bs-primary)", cursor: "pointer" }}
              />
              {opt.label}
            </label>
          ))}
        </div>
        <label style={{ ...radioStyle, marginTop: 4, borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 10 }}>
          <input
            type="checkbox"
            checked={invert}
            onChange={(e) => setInvert(e.target.checked)}
            style={{ accentColor: "var(--bs-primary)", cursor: "pointer" }}
          />
          Invert mask
        </label>
      </Modal.Body>
      <Modal.Footer style={{ ...panelStyle, borderTop: "1px solid rgba(255,255,255,0.1)", padding: "8px 16px", gap: 6 }}>
        <Button variant="outline-secondary" size="sm" onClick={onHide} style={{ fontSize: 12 }}>
          Cancel
        </Button>
        <Button variant="primary" size="sm" onClick={handleAdd} style={{ fontSize: 12 }}>
          Add
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
