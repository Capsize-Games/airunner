// ── Canvas Grid Layer ───────────────────────────────────────────────────
// Renders the pixel grid on a Konva Shape layer.

import { useCallback } from "react";
import { Shape } from "react-konva";
import Konva from "konva";

interface Props {
  documentWidth: number;
  documentHeight: number;
  gridSize: number;
  gridColor: string;
}

export default function GridLayer({
  documentWidth,
  documentHeight,
  gridSize,
  gridColor,
}: Props) {
  const gridSceneFunc = useCallback(
    (ctx: Konva.Context, shape: Konva.Shape) => {
      const native = (
        ctx as unknown as { _context: CanvasRenderingContext2D }
      )._context;
      // The layer context is already scaled by the stage zoom, so a constant
      // lineWidth would scale with it. Divide by the scale to keep the grid
      // lines a constant 1px on screen while the grid spacing still scales.
      const scale = shape.getStage()?.scaleX() ?? 1;
      native.beginPath();
      // Parse hex color and apply a fixed low opacity for grid lines
      const hex = gridColor.replace("#", "");
      const r = parseInt(hex.substring(0, 2), 16);
      const g = parseInt(hex.substring(2, 4), 16);
      const b = parseInt(hex.substring(4, 6), 16);
      native.strokeStyle = `rgba(${r},${g},${b},0.25)`;
      native.lineWidth = 1 / scale;
      for (let x = 0; x <= documentWidth; x += gridSize) {
        native.moveTo(x, 0);
        native.lineTo(x, documentHeight);
      }
      for (let y = 0; y <= documentHeight; y += gridSize) {
        native.moveTo(0, y);
        native.lineTo(documentWidth, y);
      }
      native.stroke();
    },
    [documentWidth, documentHeight, gridSize, gridColor],
  );

  return <Shape sceneFunc={gridSceneFunc} />;
}
