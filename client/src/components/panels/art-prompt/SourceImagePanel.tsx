import { useEffect, useState } from "react";
import LucideIcon from "../../shared/LucideIcon";
import { useCanvasContext } from "../../../features/canvas";
import {
  renderVisibleComposite,
  visibleContentBounds,
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
  const sliderLabel = isInpaint ? "Feather" : "Strength";
  const sliderValue = isInpaint ? feather : strength;
  const onSliderChange = isInpaint ? onFeatherChange : onStrengthChange;

  // Composite every visible layer (matching the canvas) and crop the preview to
  // the actual content so the source image fills the box instead of floating in
  // the corner of the document.
  const { layers, layerGroups, displayOrder, documentWidth, documentHeight } =
    canvas;
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
      const bounds = visibleContentBounds(state);
      if (!bounds) {
        setSourceDataUrl(null);
        return;
      }
      const crop = window.document.createElement("canvas");
      crop.width = bounds.w;
      crop.height = bounds.h;
      const cctx = crop.getContext("2d");
      if (!cctx) {
        setSourceDataUrl(composite.toDataURL("image/png"));
        return;
      }
      cctx.drawImage(
        composite,
        bounds.x, bounds.y, bounds.w, bounds.h,
        0, 0, bounds.w, bounds.h,
      );
      setSourceDataUrl(crop.toDataURL("image/png"));
    })();

    return () => {
      cancelled = true;
    };
  }, [layers, layerGroups, displayOrder, documentWidth, documentHeight]);

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

      {/* Strength / Feather slider */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 8px 8px",
          background: "#0e0e16",
        }}
      >
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.07em",
            textTransform: "uppercase",
            color: "var(--theme-text-secondary)",
            opacity: 0.6,
            minWidth: 48,
          }}
        >
          {sliderLabel}
        </span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={sliderValue}
          onChange={(e) => onSliderChange(Number(e.target.value))}
          style={{ flex: 1 }}
        />
        <span
          style={{
            fontSize: 10,
            fontVariantNumeric: "tabular-nums",
            color: "var(--theme-text-secondary)",
            minWidth: 28,
            textAlign: "right",
          }}
        >
          {sliderValue.toFixed(2)}
        </span>
      </div>
    </div>
  );
}
