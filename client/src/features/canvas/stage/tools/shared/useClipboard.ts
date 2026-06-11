// ── Selection Clipboard (delete / cut / copy / paste) ─────────────────────
// Operates on the active layer's images using the current selection geometry
// from whichever selection tool is active (rectangular select, fuzzy/wand,
// or lasso). All work happens in document space and is rasterised per-image
// so the layer/image structure is preserved (no flattening of other images).
//
//   Delete            → erase the selected region from the active layer
//   Ctrl/Cmd + X      → copy the region to the clipboard, then erase it
//   Ctrl/Cmd + C      → copy the region to the clipboard
//   Ctrl/Cmd + P      → paste the clipboard onto a new layer
//
// The same four actions are exposed through the Edit menu via window events
// (edit:cut / edit:copy / edit:paste / edit:delete).

import { useCallback, useEffect, useRef } from "react";
import type { CanvasLayer, SelectionData } from "../../../canvasTypes";
import { useMenuAction } from "../../../../../components/layout/action-menu-bar/events";

// ── Types ──────────────────────────────────────────────────────────────────

interface Bounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface EdgeOptions {
  /** Feather radius in document pixels (0 = hard edge). */
  feather: number;
  /** Whether selection edges are antialiased. */
  antialias: boolean;
}

type ClipSelection =
  | ({ kind: "rect" } & Bounds & EdgeOptions)
  | ({ kind: "poly"; points: number[]; bounds: Bounds } & EdgeOptions);

export type ClipboardAction =
  | "copy" | "cut" | "paste" | "delete" | "select-all" | "select-none";

export interface UseClipboardParams {
  layers: CanvasLayer[];
  activeLayerId: string | null;
  /** The shared, tool-independent selection (null = nothing selected). */
  selection: SelectionData | null;
  clearSelection: () => void;
  selectAll: () => void;
  placeImageOnNewLayer: (
    base64: string, x: number, y: number, width: number, height: number,
  ) => void;
  updateImageSrc: (layerId: string, imageId: string, src: string) => void;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function polygonBounds(points: number[]): Bounds {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let i = 0; i < points.length; i += 2) {
    const x = points[i];
    const y = points[i + 1];
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  }
  return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

function selectionBounds(sel: ClipSelection): Bounds {
  return sel.kind === "rect" ? sel : sel.bounds;
}

/** Trace the selection outline onto a 2D context, mapping each document-space
 *  point through `map` (e.g. to crop-canvas or image-pixel space). */
function tracePath(
  ctx: CanvasRenderingContext2D,
  sel: ClipSelection,
  map: (x: number, y: number) => { x: number; y: number },
): void {
  ctx.beginPath();
  if (sel.kind === "rect") {
    const a = map(sel.x, sel.y);
    const b = map(sel.x + sel.width, sel.y);
    const c = map(sel.x + sel.width, sel.y + sel.height);
    const d = map(sel.x, sel.y + sel.height);
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.lineTo(c.x, c.y);
    ctx.lineTo(d.x, d.y);
  } else {
    const pts = sel.points;
    const p0 = map(pts[0], pts[1]);
    ctx.moveTo(p0.x, p0.y);
    for (let i = 2; i < pts.length; i += 2) {
      const p = map(pts[i], pts[i + 1]);
      ctx.lineTo(p.x, p.y);
    }
  }
  ctx.closePath();
}

/**
 * Render the selection shape into an alpha mask canvas (white = selected).
 * Antialiasing and feathering are baked into the mask's alpha channel, so it
 * can be composited (destination-in to keep / destination-out to erase) to
 * give soft selection edges.
 *
 * @param scaleFeather Multiplier applied to the feather radius — used when the
 *                     mask is built in scaled (image-pixel) space.
 */
function buildMaskCanvas(
  width: number,
  height: number,
  sel: ClipSelection,
  map: (x: number, y: number) => { x: number; y: number },
  scaleFeather = 1,
): HTMLCanvasElement {
  const W = Math.max(1, Math.round(width));
  const H = Math.max(1, Math.round(height));
  const mask = document.createElement("canvas");
  mask.width = W;
  mask.height = H;
  const mx = mask.getContext("2d");
  if (!mx) return mask;

  mx.fillStyle = "#fff";
  tracePath(mx, sel, map);
  mx.fill();

  // Hard-edge (antialiasing off, no feather): threshold the AA fringe away.
  if (!sel.antialias && sel.feather <= 0) {
    const id = mx.getImageData(0, 0, W, H);
    const d = id.data;
    for (let i = 3; i < d.length; i += 4) d[i] = d[i] >= 128 ? 255 : 0;
    mx.putImageData(id, 0, 0);
    return mask;
  }

  // Feather: blur the mask alpha for a soft falloff.
  if (sel.feather > 0) {
    const r = sel.feather * scaleFeather;
    const blurred = document.createElement("canvas");
    blurred.width = W;
    blurred.height = H;
    const bx = blurred.getContext("2d");
    if (bx) {
      bx.filter = `blur(${r}px)`;
      bx.drawImage(mask, 0, 0);
      return blurred;
    }
  }

  return mask;
}

function boundsIntersect(a: Bounds, b: Bounds): boolean {
  return !(
    a.x > b.x + b.width ||
    a.x + a.width < b.x ||
    a.y > b.y + b.height ||
    a.y + a.height < b.y
  );
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useClipboard(params: UseClipboardParams) {
  // Keep the latest props in a ref so the once-mounted key/menu listeners read
  // current state without re-subscribing every render.
  const ref = useRef(params);
  useEffect(() => {
    ref.current = params;
  });

  // Session clipboard. A ref (not state) — pasting doesn't need a re-render.
  const clipboardRef = useRef<
    { dataURL: string; x: number; y: number; width: number; height: number } | null
  >(null);

  // ── Resolve the active selection geometry ────────────────────────────
  const currentSelection = useCallback((): ClipSelection | null => {
    const s = ref.current.selection;
    if (!s || s.points.length < 6) return null;
    return {
      kind: "poly",
      points: s.points,
      bounds: s.bounds ?? polygonBounds(s.points),
      feather: s.feather,
      antialias: s.antialias,
    };
  }, []);

  const activeLayer = useCallback((): CanvasLayer | null => {
    const p = ref.current;
    return p.layers.find((l) => l.id === p.activeLayerId) ?? null;
  }, []);

  // ── Copy the selected region of the active layer to the clipboard ────
  const doCopy = useCallback(async (): Promise<boolean> => {
    const sel = currentSelection();
    const layer = activeLayer();
    if (!sel || !layer) return false;

    const b = selectionBounds(sel);
    const W = Math.max(1, Math.round(b.width));
    const H = Math.max(1, Math.round(b.height));
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d");
    if (!ctx) return false;

    for (const img of layer.images) {
      const el = await loadImage(img.src);
      ctx.drawImage(
        el,
        layer.offsetX + img.x - b.x,
        layer.offsetY + img.y - b.y,
        img.width,
        img.height,
      );
    }
    // Apply the (optionally feathered/antialiased) selection mask to the
    // composited region: destination-in keeps only the selected pixels.
    const maskC = buildMaskCanvas(W, H, sel, (x, y) => ({
      x: x - b.x,
      y: y - b.y,
    }));
    ctx.globalCompositeOperation = "destination-in";
    ctx.drawImage(maskC, 0, 0);
    ctx.globalCompositeOperation = "source-over";

    clipboardRef.current = {
      dataURL: canvas.toDataURL("image/png"),
      x: b.x,
      y: b.y,
      width: W,
      height: H,
    };
    return true;
  }, [currentSelection, activeLayer]);

  // ── Erase the selected region from each image of the active layer ────
  const doDelete = useCallback(async (): Promise<boolean> => {
    const sel = currentSelection();
    const layer = activeLayer();
    if (!sel || !layer) return false;

    const selB = selectionBounds(sel);
    let changed = false;
    for (const img of layer.images) {
      const imgB: Bounds = {
        x: layer.offsetX + img.x,
        y: layer.offsetY + img.y,
        width: img.width,
        height: img.height,
      };
      if (!boundsIntersect(selB, imgB)) continue;

      const el = await loadImage(img.src);
      const nW = el.naturalWidth || img.width;
      const nH = el.naturalHeight || img.height;
      const c = document.createElement("canvas");
      c.width = nW;
      c.height = nH;
      const cx = c.getContext("2d");
      if (!cx) continue;
      cx.drawImage(el, 0, 0, nW, nH);

      // Map document-space → this image's natural-pixel space, build the
      // (optionally feathered/antialiased) mask there, and punch it out with
      // destination-out so feathered edges erase partially.
      const sx = nW / img.width;
      const sy = nH / img.height;
      const maskC = buildMaskCanvas(
        nW,
        nH,
        sel,
        (x, y) => ({ x: (x - imgB.x) * sx, y: (y - imgB.y) * sy }),
        (sx + sy) / 2,
      );
      cx.globalCompositeOperation = "destination-out";
      cx.drawImage(maskC, 0, 0);
      cx.globalCompositeOperation = "source-over";

      ref.current.updateImageSrc(layer.id, img.id, c.toDataURL("image/png"));
      changed = true;
    }
    return changed;
  }, [currentSelection, activeLayer]);

  const doCut = useCallback(async (): Promise<boolean> => {
    const copied = await doCopy();
    if (!copied) return false;
    return doDelete();
  }, [doCopy, doDelete]);

  const doPaste = useCallback((): boolean => {
    const clip = clipboardRef.current;
    if (!clip) return false;
    ref.current.placeImageOnNewLayer(
      clip.dataURL, clip.x, clip.y, clip.width, clip.height,
    );
    return true;
  }, []);

  // ── Stable dispatcher (used by key + menu listeners) ─────────────────
  const perform = useCallback(
    (action: ClipboardAction) => {
      switch (action) {
        case "copy": void doCopy(); break;
        case "cut": void doCut(); break;
        case "delete": void doDelete(); break;
        case "paste": doPaste(); break;
        case "select-all": ref.current.selectAll(); break;
        case "select-none": ref.current.clearSelection(); break;
      }
    },
    [doCopy, doCut, doDelete, doPaste],
  );
  const performRef = useRef(perform);
  useEffect(() => {
    performRef.current = perform;
  }, [perform]);

  const hasSelection = useCallback(
    () => currentSelection() !== null,
    [currentSelection],
  );

  // ── Keyboard shortcuts ───────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      const tag = t.tagName;
      if (
        tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" ||
        t.isContentEditable
      ) {
        return;
      }
      const mod = e.ctrlKey || e.metaKey;

      if (!mod && (e.key === "Delete" || e.key === "Backspace")) {
        if (hasSelection()) {
          e.preventDefault();
          performRef.current("delete");
        }
        return;
      }
      if (mod && (e.key === "c" || e.key === "C")) {
        if (hasSelection()) {
          e.preventDefault();
          performRef.current("copy");
        }
        return;
      }
      if (mod && (e.key === "x" || e.key === "X")) {
        if (hasSelection()) {
          e.preventDefault();
          performRef.current("cut");
        }
        return;
      }
      if (mod && (e.key === "v" || e.key === "V")) {
        if (clipboardRef.current) {
          e.preventDefault();
          performRef.current("paste");
        }
        return;
      }
      if (mod && (e.key === "a" || e.key === "A")) {
        // Ctrl/Cmd+A → Select All; +Shift → Select None.
        e.preventDefault();
        performRef.current(e.shiftKey ? "select-none" : "select-all");
        return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [hasSelection]);

  // ── Edit / Select menu actions ───────────────────────────────────────
  useMenuAction((action) => {
    switch (action.type) {
      case "edit:cut": performRef.current("cut"); break;
      case "edit:copy": performRef.current("copy"); break;
      case "edit:paste": performRef.current("paste"); break;
      case "edit:delete": performRef.current("delete"); break;
      case "select:all": performRef.current("select-all"); break;
      case "select:none": performRef.current("select-none"); break;
    }
  });
}
