// ── Canvas Grid Layer ───────────────────────────────────────────────────
// Renders the pixel grid on a Konva Shape layer.

import { useCallback } from "react";
import { Shape } from "react-konva";
import Konva from "konva";
import { GRID_SIZE } from "./types";

interface Props {
  documentWidth: number;
  documentHeight: number;
}

export default function GridLayer({
  documentWidth,
  documentHeight,
}: Props) {
  const gridSceneFunc = useCallback(
    (ctx: Konva.Context) => {
      const native = (
        ctx as unknown as { _context: CanvasRenderingContext2D }
      )._context;
      native.beginPath();
      native.strokeStyle = "rgba(255,255,255,0.09)";
      native.lineWidth = 0.5;
      for (let x = 0; x <= documentWidth; x += GRID_SIZE) {
        native.moveTo(x, 0);
        native.lineTo(x, documentHeight);
      }
      for (let y = 0; y <= documentHeight; y += GRID_SIZE) {
        native.moveTo(0, y);
        native.lineTo(documentHeight, y);
      }
      native.stroke();
    },
    [documentWidth, documentHeight],
  );

  return <Shape sceneFunc={gridSceneFunc} />;
}
