// ── Pixel Ruler ───────────────────────────────────────────────────────────
// GIMP-style pixel rulers anchored to the left and top of the canvas area.
// Uses HTML canvas overlays with requestAnimationFrame to track stage
// position and zoom without additional state plumbing.

import { useEffect, useRef, useCallback } from "react";
import Konva from "konva";

const RULER_SIZE = 24; // px — width of vertical ruler, height of horizontal

interface Props {
  stageRef: React.RefObject<Konva.Stage>;
  stageSize: { width: number; height: number };
  showRuler: boolean;
}

/** Choose a "nice" tick interval based on the current zoom. */
function tickInterval(pxPerDocPixel: number): number {
  // We want labelled ticks roughly every 60–150 screen pixels.
  const raw = 80 / Math.max(pxPerDocPixel, 0.001);
  // Snap to a nice power-of-10 step.
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const residual = raw / mag;
  if (residual < 1.5) return mag;
  if (residual < 3.5) return 2 * mag;
  if (residual < 7.5) return 5 * mag;
  return 10 * mag;
}

/** Choose a minor tick interval (1/5 of major if zoomed enough). */
function minorInterval(major: number, pxPerDocPixel: number): number {
  const screenSpacing = major * pxPerDocPixel / 5;
  // Show minor ticks only if each subdivision is at least 10 screen px.
  return screenSpacing >= 10 ? major / 5 : major / 2;
}

export default function PixelRuler({
  stageRef,
  stageSize,
  showRuler,
}: Props) {
  const hCanvasRef = useRef<HTMLCanvasElement>(null);
  const vCanvasRef = useRef<HTMLCanvasElement>(null);
  const cornerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef(0);

  const drawRulers = useCallback(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const scale = stage.scaleX();
    const pos = stage.position();
    const stageW = stageSize.width;
    const stageH = stageSize.height;

    // Visible document range.
    // Rulers are offset by RULER_SIZE to leave room for the orthogonal ruler.
    const docStartX = (RULER_SIZE - pos.x) / scale;
    const docStartY = (RULER_SIZE - pos.y) / scale;
    const docEndX = docStartX + (stageW - RULER_SIZE) / scale;
    const docEndY = docStartY + (stageH - RULER_SIZE) / scale;

    const pxPerDoc = scale;
    const major = tickInterval(pxPerDoc);
    const minor = minorInterval(major, pxPerDoc);
    const tiny = major / 10;

    // ── Horizontal ruler ──────────────────────────────────────────────
    const hCtx = hCanvasRef.current?.getContext("2d");
    if (hCtx) {
      const cw = hCtx.canvas.width;
      const ch = hCtx.canvas.height;
      hCtx.clearRect(0, 0, cw, ch);

      // Background
      hCtx.fillStyle = "#1a1a24";
      hCtx.fillRect(0, 0, cw, ch);

      // Top border
      hCtx.strokeStyle = "rgba(255,255,255,0.12)";
      hCtx.lineWidth = 1;
      hCtx.beginPath();
      hCtx.moveTo(0, ch - 0.5);
      hCtx.lineTo(cw, ch - 0.5);
      hCtx.stroke();

      // Find first tick >= docStartX
      const firstMajor = Math.ceil(docStartX / major) * major;
      const firstMinor = Math.ceil(docStartX / minor) * minor;
      const firstTiny = Math.ceil(docStartX / tiny) * tiny;

      // Tiny ticks (only when pxPerDoc >= 0.5 to avoid clutter)
      if (pxPerDoc >= 0.5) {
        hCtx.strokeStyle = "rgba(255,255,255,0.15)";
        hCtx.lineWidth = 1;
        hCtx.beginPath();
        for (let docX = firstTiny; docX <= docEndX; docX += tiny) {
          // Skip positions that will be drawn as minor or major ticks
          if (Math.abs(docX % minor) < 0.001 || Math.abs(docX % major) < 0.001) continue;
          const sx = (docX - docStartX) * pxPerDoc;
          hCtx.moveTo(sx, ch - 4);
          hCtx.lineTo(sx, ch);
        }
        hCtx.stroke();
      }

      // Minor ticks
      if (minor * pxPerDoc >= 10) {
        hCtx.strokeStyle = "rgba(255,255,255,0.25)";
        hCtx.lineWidth = 1;
        hCtx.beginPath();
        for (let docX = firstMinor; docX <= docEndX; docX += minor) {
          if (Math.abs(docX % major) < 0.001) continue; // skip major positions
          const sx = (docX - docStartX) * pxPerDoc;
          hCtx.moveTo(sx, ch - 8);
          hCtx.lineTo(sx, ch);
        }
        hCtx.stroke();
      }

      // Major ticks + labels
      hCtx.fillStyle = "rgba(255,255,255,0.55)";
      hCtx.font = "9px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
      hCtx.textAlign = "center";
      hCtx.textBaseline = "top";
      hCtx.strokeStyle = "rgba(255,255,255,0.45)";
      hCtx.lineWidth = 1;
      for (let docX = firstMajor; docX <= docEndX; docX += major) {
        const sx = (docX - docStartX) * pxPerDoc;
        hCtx.beginPath();
        hCtx.moveTo(sx, ch - 14);
        hCtx.lineTo(sx, ch);
        hCtx.stroke();
        hCtx.fillText(String(docX), sx, 2);
      }
    }

    // ── Vertical ruler ────────────────────────────────────────────────
    const vCtx = vCanvasRef.current?.getContext("2d");
    if (vCtx) {
      const cw = vCtx.canvas.width;
      const ch = vCtx.canvas.height;
      vCtx.clearRect(0, 0, cw, ch);

      // Background
      vCtx.fillStyle = "#1a1a24";
      vCtx.fillRect(0, 0, cw, ch);

      // Right border
      vCtx.strokeStyle = "rgba(255,255,255,0.12)";
      vCtx.lineWidth = 1;
      vCtx.beginPath();
      vCtx.moveTo(cw - 0.5, 0);
      vCtx.lineTo(cw - 0.5, ch);
      vCtx.stroke();

      // Find first tick >= docStartY
      const firstMajor = Math.ceil(docStartY / major) * major;
      const firstMinor = Math.ceil(docStartY / minor) * minor;
      const firstTiny = Math.ceil(docStartY / tiny) * tiny;

      // Tiny ticks
      if (pxPerDoc >= 0.5) {
        vCtx.strokeStyle = "rgba(255,255,255,0.15)";
        vCtx.lineWidth = 1;
        vCtx.beginPath();
        for (let docY = firstTiny; docY <= docEndY; docY += tiny) {
          if (Math.abs(docY % minor) < 0.001 || Math.abs(docY % major) < 0.001) continue;
          const sy = (docY - docStartY) * pxPerDoc;
          vCtx.moveTo(cw - 4, sy);
          vCtx.lineTo(cw, sy);
        }
        vCtx.stroke();
      }

      // Minor ticks
      if (minor * pxPerDoc >= 10) {
        vCtx.strokeStyle = "rgba(255,255,255,0.25)";
        vCtx.lineWidth = 1;
        vCtx.beginPath();
        for (let docY = firstMinor; docY <= docEndY; docY += minor) {
          if (Math.abs(docY % major) < 0.001) continue;
          const sy = (docY - docStartY) * pxPerDoc;
          vCtx.moveTo(cw - 8, sy);
          vCtx.lineTo(cw, sy);
        }
        vCtx.stroke();
      }

      // Major ticks + labels (rotated)
      vCtx.fillStyle = "rgba(255,255,255,0.55)";
      vCtx.font = "9px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
      vCtx.textAlign = "right";
      vCtx.textBaseline = "middle";
      vCtx.strokeStyle = "rgba(255,255,255,0.45)";
      vCtx.lineWidth = 1;
      for (let docY = firstMajor; docY <= docEndY; docY += major) {
        const sy = (docY - docStartY) * pxPerDoc;
        vCtx.beginPath();
        vCtx.moveTo(cw - 14, sy);
        vCtx.lineTo(cw, sy);
        vCtx.stroke();
        vCtx.save();
        vCtx.translate(cw - 16, sy);
        vCtx.rotate(-Math.PI / 2);
        vCtx.fillText(String(docY), 0, 0);
        vCtx.restore();
      }
    }
  }, [stageRef, stageSize]);

  // ── Animation loop ──────────────────────────────────────────────────────
  useEffect(() => {
    let running = true;
    const loop = () => {
      if (!running) return;
      drawRulers();
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [drawRulers]);

  // ── Sync canvas dimensions with container ───────────────────────────────
  useEffect(() => {
    const hCanvas = hCanvasRef.current;
    const vCanvas = vCanvasRef.current;
    if (!hCanvas || !vCanvas) return;
    const dpr = window.devicePixelRatio || 1;
    const hw = stageSize.width - RULER_SIZE;
    const vh = stageSize.height - RULER_SIZE;

    // Horizontal ruler: (full width - RULER_SIZE) x RULER_SIZE
    hCanvas.width = hw * dpr;
    hCanvas.height = RULER_SIZE * dpr;
    hCanvas.style.width = `${hw}px`;
    hCanvas.style.height = `${RULER_SIZE}px`;
    hCanvas.getContext("2d")?.scale(dpr, dpr);

    // Vertical ruler: RULER_SIZE x (full height - RULER_SIZE)
    vCanvas.width = RULER_SIZE * dpr;
    vCanvas.height = vh * dpr;
    vCanvas.style.width = `${RULER_SIZE}px`;
    vCanvas.style.height = `${vh}px`;
    vCanvas.getContext("2d")?.scale(dpr, dpr);
  }, [stageSize]);

  return (
    <>
      {/* Horizontal ruler */}
      <canvas
        ref={hCanvasRef}
        style={{
          position: "absolute",
          top: 0,
          left: RULER_SIZE,
          display: showRuler ? "block" : "none",
          pointerEvents: "none",
        }}
      />
      {/* Vertical ruler */}
      <canvas
        ref={vCanvasRef}
        style={{
          position: "absolute",
          top: RULER_SIZE,
          left: 0,
          display: showRuler ? "block" : "none",
          pointerEvents: "none",
        }}
      />
      {/* Corner square */}
      <div
        ref={cornerRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: RULER_SIZE,
          height: RULER_SIZE,
          background: "#1a1a24",
          borderRight: "1px solid rgba(255,255,255,0.12)",
          borderBottom: "1px solid rgba(255,255,255,0.12)",
          pointerEvents: "none",
          display: showRuler ? "block" : "none",
        }}
      />
    </>
  );
}
