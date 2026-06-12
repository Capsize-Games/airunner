import { useEffect, useRef } from "react";
import type { CanvasLayer } from "./useCanvasState";

const SQ = 4; // checkerboard square size

function drawCheckerboard(ctx: CanvasRenderingContext2D, w: number, h: number) {
  for (let y = 0; y < h; y += SQ) {
    for (let x = 0; x < w; x += SQ) {
      ctx.fillStyle = (x / SQ + y / SQ) % 2 === 0 ? "#444" : "#2a2a2a";
      ctx.fillRect(x, y, SQ, SQ);
    }
  }
}

interface Props {
  layer: CanvasLayer;
  docWidth: number;
  docHeight: number;
  type: "content" | "mask";
  active?: boolean;
  size?: number;
  onClick?: (e: React.MouseEvent) => void;
}

export default function LayerThumbnail({
  layer,
  docWidth,
  docHeight,
  type,
  active = false,
  size = 32,
  onClick,
}: Props) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ctx = el.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, size, size);
    drawCheckerboard(ctx, size, size);

    const scale = Math.min(size / docWidth, size / docHeight);
    const scaledW = docWidth * scale;
    const scaledH = docHeight * scale;
    const ox = (size - scaledW) / 2;
    const oy = (size - scaledH) / 2;

    ctx.save();
    ctx.translate(ox, oy);
    ctx.scale(scale, scale);
    ctx.beginPath();
    ctx.rect(0, 0, docWidth, docHeight);
    ctx.clip();

    if (type === "mask" && Array.isArray(layer.maskStrokes)) {
      // Draw mask as grayscale (white = reveal, black = hide)
      ctx.fillStyle = layer.maskFill === "black" ? "#000" : "#fff";
      ctx.fillRect(0, 0, docWidth, docHeight);
      for (const stroke of layer.maskStrokes) {
        if (stroke.points.length < 4) continue;
        ctx.beginPath();
        ctx.strokeStyle = stroke.color;
        ctx.lineWidth = stroke.strokeWidth;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.moveTo(stroke.points[0], stroke.points[1]);
        for (let i = 2; i < stroke.points.length; i += 2) {
          ctx.lineTo(stroke.points[i], stroke.points[i + 1]);
        }
        ctx.stroke();
      }
    } else if (type === "content") {
      if (layer.fillColor && layer.fillColor !== "transparent") {
        ctx.fillStyle = layer.fillColor;
        ctx.fillRect(0, 0, docWidth, docHeight);
      }
      for (const stroke of layer.strokes) {
        if (stroke.points.length < 4) continue;
        ctx.beginPath();
        if (stroke.tool === "eraser") ctx.globalCompositeOperation = "destination-out";
        ctx.strokeStyle = stroke.color;
        ctx.lineWidth = stroke.strokeWidth;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.moveTo(stroke.points[0], stroke.points[1]);
        for (let i = 2; i < stroke.points.length; i += 2) {
          ctx.lineTo(stroke.points[i], stroke.points[i + 1]);
        }
        ctx.stroke();
        if (stroke.tool === "eraser") ctx.globalCompositeOperation = "source-over";
      }
    }

    ctx.restore();

    // Async image drawing for content thumbnails — load all images in
    // parallel so layers with many images render at the same time.
    if (type === "content" && layer.images.length > 0) {
      (async () => {
        const canvas = ref.current;
        if (!canvas) return;
        const ctx2 = canvas.getContext("2d");
        if (!ctx2) return;
        ctx2.save();
        ctx2.translate(ox, oy);
        ctx2.scale(scale, scale);
        ctx2.beginPath();
        ctx2.rect(0, 0, docWidth, docHeight);
        ctx2.clip();
        const loadOne = (src: string): Promise<HTMLImageElement | null> =>
          new Promise((resolve) => {
            const el = new window.Image();
            el.onload = () => resolve(el);
            el.onerror = () => resolve(null);
            el.src = src;
          });
        const loaded = await Promise.all(
          layer.images.map((img) => loadOne(img.src)),
        );
        for (let i = 0; i < layer.images.length; i++) {
          const img = layer.images[i];
          const el = loaded[i];
          if (el) {
            ctx2.drawImage(el, img.x, img.y, img.width, img.height);
          }
        }
        ctx2.restore();
      })();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layer.maskStrokes, layer.maskFill, layer.strokes, layer.images, layer.fillColor, docWidth, docHeight, size, type]);

  return (
    <canvas
      ref={ref}
      width={size}
      height={size}
      onClick={onClick}
      title={type === "mask" ? "Mask (click to edit)" : "Layer content (click to edit)"}
      style={{
        width: size,
        height: size,
        flexShrink: 0,
        borderRadius: 2,
        display: "block",
        cursor: onClick ? "pointer" : "default",
        outline: active ? "2px solid #fff" : "1px solid rgba(255,255,255,0.18)",
        outlineOffset: -1,
      }}
    />
  );
}
