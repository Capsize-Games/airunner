// ── Crop Tool Rendering Layer ──────────────────────────────────────────
// Pure Konva rendering — no interaction logic beyond wiring Transformer
// callbacks back to the parent hook.
//
// Renders:
//   • A dark semi-transparent overlay covering the entire stage
//   • A clear "cutout" where the crop area is (via globalCompositeOperation)
//   • An invisible rect + Transformer for interactive resize handles

import { useRef, useCallback } from "react";
import { Layer, Rect, Transformer, Shape } from "react-konva";
import Konva from "konva";
import type { CropRenderState } from "./useCropTool";

// ── Props ─────────────────────────────────────────────────────────────────

interface Props extends CropRenderState {
  stageWidth: number;
  stageHeight: number;
  onCropRectChange: (
    x: number, y: number,
    width: number, height: number,
  ) => void;
}

// ── Component ─────────────────────────────────────────────────────────────

export default function CropLayer({
  cropX, cropY, cropWidth, cropHeight,
  isAdjusting,
  stageWidth, stageHeight,
  onCropRectChange,
}: Props) {
  const transformerRef = useRef<Konva.Transformer | null>(null);
  const cropRectRef = useRef<Konva.Rect | null>(null);

  // ── Transformer event callbacks ────────────────────────────────────

  const handleTransform = useCallback(() => {
    const node = cropRectRef.current;
    if (!node) return;
    // Account for scale when the Transformer resizes
    const w = Math.max(8, node.width() * node.scaleX());
    const h = Math.max(8, node.height() * node.scaleY());
    node.scaleX(1);
    node.scaleY(1);
    onCropRectChange(node.x(), node.y(), w, h);
  }, [onCropRectChange]);

  const handleDragMove = useCallback(() => {
    const node = cropRectRef.current;
    if (!node) return;
    onCropRectChange(
      node.x(),
      node.y(),
      node.width(),
      node.height(),
    );
  }, [onCropRectChange]);

  const handleTransformEnd = useCallback(() => {
    const node = cropRectRef.current;
    if (!node) return;
    const w = Math.max(8, node.width() * node.scaleX());
    const h = Math.max(8, node.height() * node.scaleY());
    node.scaleX(1);
    node.scaleY(1);
    onCropRectChange(node.x(), node.y(), w, h);
  }, [onCropRectChange]);

  const handleDragEnd = useCallback(() => {
    const node = cropRectRef.current;
    if (!node) return;
    onCropRectChange(
      node.x(),
      node.y(),
      node.width(),
      node.height(),
    );
  }, [onCropRectChange]);

  // ── Dark overlay scene function ────────────────────────────────────

  const overlaySceneFunc = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (ctx: Konva.Context, shape: Konva.Shape) => {
      const w = stageWidth;
      const h = stageHeight;
      // Draw the full dark overlay
      ctx.beginPath();
      ctx.fillStyle = "rgba(0, 0, 0, 0.5)";
      ctx.fillRect(0, 0, w, h);
      // Cut out the crop area using destination-out composite
      ctx.globalCompositeOperation = "destination-out";
      ctx.beginPath();
      ctx.fillStyle = "rgba(0, 0, 0, 1)";
      ctx.fillRect(
        Math.round(cropX),
        Math.round(cropY),
        Math.round(cropWidth),
        Math.round(cropHeight),
      );
      // Reset composite operation
      ctx.globalCompositeOperation = "source-over";
    },
    [stageWidth, stageHeight, cropX, cropY, cropWidth, cropHeight],
  );

  // Nothing to show if crop rect is zero-sized
  const nothingVisible = cropWidth < 1 || cropHeight < 1;

  return (
    <Layer listening={false}>
      {/* Dark overlay with crop cutout */}
      {!nothingVisible && (
        <Shape
          x={0}
          y={0}
          width={stageWidth}
          height={stageHeight}
          sceneFunc={overlaySceneFunc}
          listening={false}
        />
      )}

      {/* Interactive crop layer (handles Transformer drag/resize) */}
      {!nothingVisible && isAdjusting && (
        <Layer listening={true}>
          <Rect
            ref={cropRectRef}
            x={cropX}
            y={cropY}
            width={cropWidth}
            height={cropHeight}
            fill="transparent"
            stroke="#6399ff"
            strokeWidth={1}
            dash={[5, 3]}
            strokeScaleEnabled={false}
            draggable
            onTransform={handleTransform}
            onDragMove={handleDragMove}
            onTransformEnd={handleTransformEnd}
            onDragEnd={handleDragEnd}
          />
          <Transformer
            ref={transformerRef}
            boundBoxFunc={(_old, newBox) => {
              // Clamp minimum size
              if (newBox.width < 8) newBox.width = 8;
              if (newBox.height < 8) newBox.height = 8;
              return newBox;
            }}
            borderStroke="#6399ff"
            borderStrokeWidth={1}
            anchorFill="#6399ff"
            anchorStroke="#fff"
            anchorSize={8}
            anchorCornerRadius={2}
            rotateEnabled={false}
            enabledAnchors={[
              "top-left", "top-center", "top-right",
              "middle-left", "middle-right",
              "bottom-left", "bottom-center", "bottom-right",
            ]}
          />
        </Layer>
      )}

      {/* When still drawing, show a dashed outline without handles */}
      {!nothingVisible && !isAdjusting && (
        <Rect
          x={cropX}
          y={cropY}
          width={cropWidth}
          height={cropHeight}
          fill="transparent"
          stroke="#6399ff"
          strokeWidth={1}
          dash={[5, 3]}
          strokeScaleEnabled={false}
          listening={false}
        />
      )}
    </Layer>
  );
}
