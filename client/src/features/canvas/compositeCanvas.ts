// ── Canvas Compositing ───────────────────────────────────────────────────────
// Renders all *visible* layers (respecting display order, group visibility,
// per-layer opacity, offset, fill, images, strokes and text) onto a single
// document-sized canvas. Used by the img2img / inpaint source preview and as
// the init image handed to the generation pipeline.

import type { CanvasLayer, LayerGroup, StrokeNode } from "./canvasTypes";

export interface CompositeState {
  layers: CanvasLayer[];
  layerGroups: LayerGroup[];
  displayOrder: string[];
  documentWidth: number;
  documentHeight: number;
}

/**
 * Flatten `displayOrder` into a bottom-to-top list of the layers that are
 * actually visible — a layer is visible only when its own `visible` flag is
 * set and its parent group (if any) is visible. Mirrors the ordering logic in
 * StageContent so the composite matches what is drawn on the stage.
 */
export function orderVisibleLayers(s: CompositeState): CanvasLayer[] {
  const groupVisible = (id: string | null | undefined): boolean => {
    if (!id) return true;
    const g = s.layerGroups.find((grp) => grp.id === id);
    return g ? g.visible : true;
  };

  const result: CanvasLayer[] = [];
  const seen = new Set<string>();
  const push = (layer: CanvasLayer) => {
    if (seen.has(layer.id)) return;
    seen.add(layer.id);
    if (layer.visible && groupVisible(layer.parentGroupId)) {
      result.push(layer);
    }
  };

  for (const id of s.displayOrder) {
    const group = s.layerGroups.find((g) => g.id === id);
    if (group) {
      for (const child of s.layers.filter((l) => l.parentGroupId === id)) {
        push(child);
      }
      continue;
    }
    const layer = s.layers.find((l) => l.id === id);
    if (layer) push(layer);
  }
  for (const layer of s.layers) push(layer);
  return result;
}

function loadImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const el = new window.Image();
    el.onload = () => resolve(el);
    el.onerror = () => resolve(null);
    el.src = src;
  });
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: StrokeNode) {
  const pts = stroke.points;
  if (pts.length < 4) return;
  ctx.save();
  if (stroke.tool === "eraser") {
    ctx.globalCompositeOperation = "destination-out";
  }
  ctx.beginPath();
  ctx.strokeStyle = stroke.color;
  ctx.lineWidth = stroke.strokeWidth;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.moveTo(pts[0], pts[1]);
  for (let i = 2; i < pts.length; i += 2) ctx.lineTo(pts[i], pts[i + 1]);
  ctx.stroke();
  ctx.restore();
}

/**
 * Draw a single layer's content into `ctx`, matching the stage z-order:
 * fill → images → strokes → text. The caller is responsible for per-layer
 * opacity; this renders the layer at full opacity so eraser strokes only cut
 * into that layer's own pixels.
 */
async function drawLayerContent(
  ctx: CanvasRenderingContext2D,
  layer: CanvasLayer,
  docW: number,
  docH: number,
) {
  ctx.save();
  ctx.translate(layer.offsetX, layer.offsetY);

  if (layer.fillColor && layer.fillColor !== "transparent") {
    ctx.fillStyle = layer.fillColor;
    ctx.fillRect(-layer.offsetX, -layer.offsetY, docW, docH);
  }

  for (const img of layer.images) {
    const el = await loadImage(img.src);
    if (el) ctx.drawImage(el, img.x, img.y, img.width, img.height);
  }

  for (const stroke of layer.strokes) drawStroke(ctx, stroke);

  if (layer.textNode) {
    const t = layer.textNode;
    ctx.font = `${t.fontSize}px ${t.fontFamily}`;
    ctx.fillStyle = t.fill;
    ctx.fillText(t.text, t.x, t.y);
  }

  ctx.restore();
}

/**
 * Render every visible layer onto a single document-sized canvas. Each layer is
 * drawn to its own offscreen buffer first so per-layer opacity and eraser
 * compositing stay isolated, then flattened with the layer's opacity. Returns
 * `null` when there is nothing visible to draw or the document has no size.
 */
export async function renderVisibleComposite(
  s: CompositeState,
): Promise<HTMLCanvasElement | null> {
  const docW = s.documentWidth;
  const docH = s.documentHeight;
  if (docW <= 0 || docH <= 0) return null;

  const visible = orderVisibleLayers(s);
  if (visible.length === 0) return null;

  const out = window.document.createElement("canvas");
  out.width = docW;
  out.height = docH;
  const octx = out.getContext("2d");
  if (!octx) return null;

  for (const layer of visible) {
    const lc = window.document.createElement("canvas");
    lc.width = docW;
    lc.height = docH;
    const lctx = lc.getContext("2d");
    if (!lctx) continue;
    await drawLayerContent(lctx, layer, docW, docH);
    octx.globalAlpha = layer.opacity ?? 1;
    octx.drawImage(lc, 0, 0);
    octx.globalAlpha = 1;
  }

  return out;
}

/**
 * Bounding box (in document-pixel space, clamped to the document) of all
 * visible content across visible layers, so a preview can be cropped to the
 * actual imagery instead of showing empty document margins. Returns `null` when
 * there is no content.
 */
export function visibleContentBounds(
  s: CompositeState,
): { x: number; y: number; w: number; h: number } | null {
  const docW = s.documentWidth;
  const docH = s.documentHeight;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const add = (ax: number, ay: number, aw: number, ah: number) => {
    minX = Math.min(minX, ax);
    minY = Math.min(minY, ay);
    maxX = Math.max(maxX, ax + aw);
    maxY = Math.max(maxY, ay + ah);
  };

  for (const layer of orderVisibleLayers(s)) {
    const ox = layer.offsetX;
    const oy = layer.offsetY;
    if (layer.fillColor && layer.fillColor !== "transparent") {
      add(0, 0, docW, docH);
    }
    for (const img of layer.images) {
      add(ox + img.x, oy + img.y, img.width, img.height);
    }
    for (const stroke of layer.strokes) {
      const hw = stroke.strokeWidth / 2;
      for (let i = 0; i < stroke.points.length; i += 2) {
        add(
          ox + stroke.points[i] - hw,
          oy + stroke.points[i + 1] - hw,
          stroke.strokeWidth,
          stroke.strokeWidth,
        );
      }
    }
    if (layer.textNode) {
      const t = layer.textNode;
      add(ox + t.x, oy + t.y - t.fontSize, t.text.length * t.fontSize * 0.6, t.fontSize * 1.3);
    }
  }

  if (!Number.isFinite(minX)) return null;
  const x = Math.max(0, Math.floor(minX));
  const y = Math.max(0, Math.floor(minY));
  const w = Math.min(docW, Math.ceil(maxX)) - x;
  const h = Math.min(docH, Math.ceil(maxY)) - y;
  if (w <= 0 || h <= 0) return null;
  return { x, y, w, h };
}
