import { useCallback } from "react";
import { Layer, Rect, Shape } from "react-konva";
import Konva from "konva";

const CHECKER_SIZE = 8;

interface CanvasBackgroundProps {
  documentWidth: number;
  documentHeight: number;
  documentBgColor: string;
  /** When true, forces a transparent checkerboard regardless of documentBgColor. */
  hasLayers: boolean;
}

/**
 * Renders the document background layer – either a checkerboard pattern
 * (when `documentBgColor === "transparent"`) or a solid filled rectangle,
 * plus the document border.
 */
export default function CanvasBackground({
  documentWidth,
  documentHeight,
  documentBgColor,
  hasLayers,
}: CanvasBackgroundProps) {
  const checkerSceneFunc = useCallback(
    (ctx: Konva.Context) => {
      const native = (
        ctx as unknown as { _context: CanvasRenderingContext2D }
      )._context;
      const cols = Math.ceil(documentWidth / CHECKER_SIZE);
      const rows = Math.ceil(documentHeight / CHECKER_SIZE);
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          native.fillStyle =
            (row + col) % 2 === 0 ? "#2a2a3a" : "#242432";
          native.fillRect(
            col * CHECKER_SIZE,
            row * CHECKER_SIZE,
            CHECKER_SIZE,
            CHECKER_SIZE,
          );
        }
      }
    },
    [documentWidth, documentHeight],
  );

  const showCheckerboard = !hasLayers || documentBgColor === "transparent";

  return (
    <Layer listening={false}>
      {showCheckerboard ? (
        <Shape sceneFunc={checkerSceneFunc} />
      ) : (
        <Rect
          x={0}
          y={0}
          width={documentWidth}
          height={documentHeight}
          fill={documentBgColor}
        />
      )}
      {/* Document border */}
      <Rect
        x={0}
        y={0}
        width={documentWidth}
        height={documentHeight}
        fill="transparent"
        stroke="rgba(255,255,255,0.15)"
        strokeWidth={1}
        listening={false}
      />
    </Layer>
  );
}
