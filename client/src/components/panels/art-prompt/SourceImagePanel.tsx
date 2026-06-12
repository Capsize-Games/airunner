import { useEffect, useState } from "react";
import { SquareDashed, Brush, Eraser, Trash2 } from "lucide-react";
import LucideIcon from "../../shared/LucideIcon";
import SliderWithSpinbox from "../SliderWithSpinbox";
import { useCanvasContext } from "../../../features/canvas";
import {
  renderVisibleComposite,
  cropToRect,
} from "../../../features/canvas/compositeCanvas";

interface SourceImagePanelProps {
  generationType: "img2img" | "inpaint";
  /** img2img denoise strength, 0–1. */
  strength: number;
  onStrengthChange: (v: number) => void;
  /** inpaint mask feather, 0–1. */
  feather: number;
  onFeatherChange: (v: number) => void;
}

export default function SourceImagePanel({
  generationType,
  strength,
  onStrengthChange,
  feather,
  onFeatherChange,
}: SourceImagePanelProps) {
  const canvas = useCanvasContext();
  const [sourceDataUrl, setSourceDataUrl] = useState<string | null>(null);

  const isInpaint = generationType === "inpaint";
  const headerLabel = isInpaint ? "Inpaint" : "Image-to-image";

  // Composite every visible layer (matching the canvas) and crop the preview to
  // the active generation area, so the preview matches exactly what will be
  // captured and generated. For inpaint, overlay the magenta mask strokes.
  const {
    layers, layerGroups, displayOrder, documentWidth, documentHeight,
    activeGridArea, inpaintMaskStrokes,
  } = canvas;
  useEffect(() => {
    let cancelled = false;
    const state = {
      layers,
      layerGroups,
      displayOrder,
      documentWidth,
      documentHeight,
    };

    (async () => {
      const composite = await renderVisibleComposite(state);
      if (cancelled) return;
      if (!composite) {
        setSourceDataUrl(null);
        return;
      }
      const crop = cropToRect(composite, activeGridArea);

      // Inpaint: overlay the magenta mask region. Build it on its own layer so
      // eraser strokes (destination-out) only cut the mask, not the source.
      if (isInpaint && inpaintMaskStrokes.length > 0) {
        const cctx = crop.getContext("2d");
        const maskC = window.document.createElement("canvas");
        maskC.width = crop.width;
        maskC.height = crop.height;
        const mctx = maskC.getContext("2d");
        if (cctx && mctx) {
          mctx.strokeStyle = "#ff00ff";
          mctx.lineCap = "round";
          mctx.lineJoin = "round";
          mctx.translate(-activeGridArea.x, -activeGridArea.y);
          for (const stroke of inpaintMaskStrokes) {
            const pts = stroke.points;
            if (pts.length < 4) continue;
            mctx.globalCompositeOperation =
              stroke.tool === "eraser" ? "destination-out" : "source-over";
            mctx.beginPath();
            mctx.lineWidth = stroke.strokeWidth;
            mctx.moveTo(pts[0], pts[1]);
            for (let i = 2; i < pts.length; i += 2) mctx.lineTo(pts[i], pts[i + 1]);
            mctx.stroke();
          }
          cctx.drawImage(maskC, 0, 0);
        }
      }

      setSourceDataUrl(crop.toDataURL("image/png"));
    })();

    return () => {
      cancelled = true;
    };
  }, [
    layers, layerGroups, displayOrder, documentWidth, documentHeight,
    activeGridArea, inpaintMaskStrokes, isInpaint,
  ]);

  const iconBtnStyle = (active: boolean, accent = "#5599ff"): React.CSSProperties => ({
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: 28,
    height: 24,
    padding: 0,
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    flexShrink: 0,
    background: active ? `${accent}33` : "transparent",
    color: active ? accent : "rgba(255,255,255,0.4)",
    boxShadow: active ? `inset 0 0 0 1.5px ${accent}88` : "none",
  });

  const toolBtn = (
    tool: "grid-area" | "inpaint-mask" | "inpaint-eraser",
    Icon: React.ComponentType<{ size?: number; strokeWidth?: number }>,
    title: string,
    accent: string,
  ) => {
    const active = canvas.activeTool === tool;
    return (
      <button
        title={title}
        onClick={() => canvas.setActiveTool(active ? "move" : tool)}
        style={iconBtnStyle(active, accent)}
      >
        <Icon size={14} strokeWidth={1.75} />
      </button>
    );
  };

  return (
    <div
      className="flex-shrink-0"
      style={{
        borderBottom: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 5,
          padding: "4px 8px",
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          color: "var(--theme-text-secondary)",
          opacity: 0.6,
          background: "#12121c",
        }}
      >
        <LucideIcon name={isInpaint ? "layers" : "image"} size={9} />
        {headerLabel}
      </div>

      {/* Source image preview */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "6px 8px",
          background: "#0e0e16",
          minHeight: 60,
        }}
      >
        {sourceDataUrl ? (
          <img
            src={sourceDataUrl}
            alt="Source image"
            style={{
              maxWidth: "100%",
              maxHeight: 120,
              borderRadius: 4,
              objectFit: "contain",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          />
        ) : (
          <span
            style={{
              fontSize: 10,
              color: "rgba(255,255,255,0.3)",
              fontStyle: "italic",
            }}
          >
            No visible layers
          </span>
        )}
      </div>

      {/* Strength (img2img + inpaint) and Feather (inpaint only) sliders */}
      <div style={{ padding: "6px 8px", background: "#0e0e16", display: "flex", flexDirection: "column", gap: 4 }}>
        <SliderWithSpinbox label="Strength" value={strength}
          min={0} max={1} step={0.01} displayAsFloat labelWidth={80}
          onChange={onStrengthChange} />
        {isInpaint && <SliderWithSpinbox label="Feather" value={feather}
          min={0} max={1} step={0.01} displayAsFloat labelWidth={80}
          onChange={onFeatherChange} />}
      </div>

      {/* Tool row: active generation area, mask brush, mask eraser, clear. */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "0 8px 8px",
          background: "#0e0e16",
        }}
      >
        {toolBtn(
          "grid-area",
          SquareDashed,
          "Active generation area — drag/resize the region",
          "#5599ff",
        )}
        {isInpaint && toolBtn(
          "inpaint-mask",
          Brush,
          "Mask brush — paint the area to regenerate",
          "#ff66ff",
        )}
        {isInpaint && toolBtn(
          "inpaint-eraser",
          Eraser,
          "Mask eraser — erase the mask",
          "#ff66ff",
        )}
        {isInpaint && (
          <button
            title="Clear mask"
            onClick={() => canvas.clearInpaintMask()}
            style={iconBtnStyle(false)}
          >
            <Trash2 size={14} strokeWidth={1.75} />
          </button>
        )}
      </div>
    </div>
  );
}
