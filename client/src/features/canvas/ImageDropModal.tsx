import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";

export type DropResizeMode = "none" | "fit-canvas";

interface ImageDropModalProps {
  show: boolean;
  naturalW: number;
  naturalH: number;
  gridW: number;
  gridH: number;
  canvasW: number;
  canvasH: number;
  onConfirm: (mode: DropResizeMode) => void;
  onHide: () => void;
}

function fitDimensions(
  srcW: number,
  srcH: number,
  maxW: number,
  maxH: number,
): { w: number; h: number } {
  const ratio = Math.min(maxW / srcW, maxH / srcH, 1);
  return { w: Math.round(srcW * ratio), h: Math.round(srcH * ratio) };
}

export default function ImageDropModal({
  show,
  naturalW,
  naturalH,
  gridW,
  gridH,
  canvasW,
  canvasH,
  onConfirm,
  onHide,
}: ImageDropModalProps) {
  const fitGrid   = fitDimensions(naturalW, naturalH, gridW, gridH);
  const fitCanvas = fitDimensions(naturalW, naturalH, canvasW, canvasH);

  const options: { mode: DropResizeMode; label: string; detail: string }[] = [
    { mode: "none",       label: "Original size",        detail: `${naturalW} × ${naturalH}` },
    { mode: "fit-canvas", label: "Fit to Canvas",        detail: `→ ${fitCanvas.w} × ${fitCanvas.h}` },
  ];

  return (
    <Modal show={show} onHide={onHide} centered size="sm" contentClassName="bg-dark text-light border-secondary">
      <Modal.Header closeButton closeVariant="white" style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        <Modal.Title style={{ fontSize: 14 }}>Place Image</Modal.Title>
      </Modal.Header>
      <Modal.Body className="d-flex flex-column gap-2">
        {options.map(({ mode, label, detail }) => (
          <button
            key={mode}
            onClick={() => { onConfirm(mode); onHide(); }}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "8px 12px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 6,
              color: "rgba(255,255,255,0.85)",
              cursor: "pointer",
              textAlign: "left",
              fontSize: 13,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(99,153,255,0.15)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.05)")}
          >
            <span>{label}</span>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", fontFamily: "monospace" }}>{detail}</span>
          </button>
        ))}
      </Modal.Body>
      <Modal.Footer style={{ borderColor: "rgba(255,255,255,0.1)" }}>
        <Button variant="outline-secondary" size="sm" onClick={onHide}>Cancel</Button>
      </Modal.Footer>
    </Modal>
  );
}

export { fitDimensions };
