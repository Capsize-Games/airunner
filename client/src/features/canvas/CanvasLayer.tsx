import { useRef, useEffect, useLayoutEffect } from "react";
import { Group, Image as KonvaImage, Layer, Line, Rect } from "react-konva";
import Konva from "konva";
import type { CanvasLayer as CanvasLayerType, StrokeNode, ActiveTool } from "./useCanvasState";
import DrawingLayer from "./DrawingLayer";

interface CanvasLayerProps {
  layer: CanvasLayerType;
  isActive: boolean;
  activeTool: ActiveTool;
  brushSize: number;
  brushColor: string;
  snapToGrid: boolean;
  canvasWidth: number;
  canvasHeight: number;
  onStrokeComplete: (stroke: Omit<StrokeNode, "id">) => void;
  onMoveImage: (layerId: string, imageId: string, x: number, y: number) => void;
  onMoveLayer: (layerId: string, x: number, y: number) => void;
}

function applyKonvaFilters(group: Konva.Group, filters: CanvasLayerType["filters"]) {
  if (!group) return;
  const konvaFilters: unknown[] = [];
  for (const f of filters) {
    switch (f.type) {
      case "blur": konvaFilters.push(Konva.Filters.Blur); break;
      case "pixelate": konvaFilters.push(Konva.Filters.Pixelate); break;
      case "noise": konvaFilters.push(Konva.Filters.Noise); break;
      case "brighten": konvaFilters.push(Konva.Filters.Brighten); break;
      case "contrast": konvaFilters.push(Konva.Filters.Contrast); break;
      case "grayscale": konvaFilters.push(Konva.Filters.Grayscale); break;
    }
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (group as any).filters(konvaFilters.length > 0 ? konvaFilters : undefined);
  for (const f of filters) {
    if (f.type === "blur") group.blurRadius(f.params.blurRadius ?? 0);
    else if (f.type === "pixelate") group.pixelSize(f.params.pixelSize ?? 4);
    else if (f.type === "noise") group.noise(f.params.noise ?? 0);
    else if (f.type === "brighten") group.brightness(f.params.brightness ?? 0);
    else if (f.type === "contrast") group.contrast(f.params.contrast ?? 0);
  }
  if (konvaFilters.length > 0) group.cache();
  else group.clearCache();
}

const VIS_SNAP = 16;
const snapVal = (v: number, on: boolean) => on ? Math.round(v / VIS_SNAP) * VIS_SNAP : v;

function LayerImage({
  node,
  isMovable,
  snapToGrid,
  onMove,
}: {
  node: CanvasLayerType["images"][0];
  isMovable: boolean;
  snapToGrid: boolean;
  onMove: (x: number, y: number) => void;
}) {
  const imageRef = useRef<Konva.Image>(null);
  const imgElementRef = useRef<HTMLImageElement | null>(null);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    const img = new window.Image();
    img.src = node.src;
    img.onload = () => {
      imgElementRef.current = img;
      if (imageRef.current) {
        imageRef.current.image(img);
        imageRef.current.getLayer()?.batchDraw();
      }
    };
  }, [node.src]);

  return (
    <KonvaImage
      ref={imageRef}
      id={node.id}
      x={node.x}
      y={node.y}
      width={node.width}
      height={node.height}
      image={imgElementRef.current ?? undefined}
      draggable={isMovable}
      onDragEnd={(e) => {
        onMove(snapVal(e.target.x(), snapToGrid), snapVal(e.target.y(), snapToGrid));
      }}
    />
  );
}

export default function CanvasLayerRenderer({
  layer,
  isActive,
  activeTool,
  brushSize,
  brushColor,
  snapToGrid,
  canvasWidth,
  canvasHeight,
  onStrokeComplete,
  onMoveImage,
  onMoveLayer,
}: CanvasLayerProps) {
  const outerGroupRef = useRef<Konva.Group>(null);   // wrapper for mask compositing (cached)
  const contentGroupRef = useRef<Konva.Group>(null);  // layer content (filters applied here)
  const maskGroupRef = useRef<Konva.Group>(null);     // mask bitmap (must be cached before outer group)
  const hasMask = Array.isArray(layer.maskStrokes);

  useEffect(() => {
    if (contentGroupRef.current) applyKonvaFilters(contentGroupRef.current, layer.filters);
  }, [layer.filters]);

  // Re-cache both the mask group and outer group when mask or content changes.
  // Mask group must be cached first so destination-in compositing works correctly:
  // its isolated offscreen canvas (white with transparent holes) is then composited
  // onto the outer group's cache via destination-in to clip the layer content.
  useLayoutEffect(() => {
    if (!hasMask) return;
    requestAnimationFrame(() => {
      const cacheBounds = {
        x: -layer.offsetX,
        y: -layer.offsetY,
        width: canvasWidth,
        height: canvasHeight,
        pixelRatio: 1,
      };
      // Cache mask group first — creates the isolated white-with-holes bitmap.
      const maskG = maskGroupRef.current;
      if (maskG) maskG.cache(cacheBounds);
      // Cache outer group second — composites masked content into its own bitmap.
      const outerG = outerGroupRef.current;
      if (!outerG) return;
      outerG.cache(cacheBounds);
      outerG.getLayer()?.batchDraw();
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMask, layer.maskStrokes, layer.maskFill, layer.images, layer.strokes, layer.offsetX, layer.offsetY, canvasWidth, canvasHeight]);

  const isLayerMovable = activeTool === "move" && isActive;

  const contentChildren = (
    <>
      {layer.images.map((img) => (
        <LayerImage
          key={img.id}
          node={img}
          isMovable={false}
          snapToGrid={snapToGrid}
          onMove={(x, y) => onMoveImage(layer.id, img.id, x, y)}
        />
      ))}
      <DrawingLayer
        strokes={layer.strokes}
        activeTool={activeTool}
        brushSize={brushSize}
        brushColor={brushColor}
        visible={layer.visible}
        opacity={layer.opacity}
        onStrokeComplete={onStrokeComplete}
        isActive={isActive}
        canvasWidth={canvasWidth}
        canvasHeight={canvasHeight}
      />
    </>
  );

  return (
    <Layer visible={layer.visible} opacity={layer.opacity}>
      {hasMask ? (
        <Group
          ref={outerGroupRef}
          x={layer.offsetX}
          y={layer.offsetY}
          draggable={isLayerMovable}
          onDragEnd={(e) => {
            const x = snapVal(e.target.x(), snapToGrid);
            const y = snapVal(e.target.y(), snapToGrid);
            e.target.x(x);
            e.target.y(y);
            onMoveLayer(layer.id, x, y);
          }}
        >
          <Group ref={contentGroupRef}>
            {contentChildren}
          </Group>
          <Group ref={maskGroupRef} globalCompositeOperation="destination-in" listening={false}>
            {layer.maskFill !== "black" && (
              <Rect
                x={-layer.offsetX}
                y={-layer.offsetY}
                width={canvasWidth}
                height={canvasHeight}
                fill="white"
              />
            )}
            {layer.maskStrokes!.map((stroke) => (
              <Line
                key={stroke.id}
                points={stroke.points}
                stroke={stroke.color}
                strokeWidth={stroke.strokeWidth}
                tension={0.5}
                lineCap="round"
                lineJoin="round"
                globalCompositeOperation={
                  stroke.color === "#000000" ? "destination-out" : "source-over"
                }
              />
            ))}
          </Group>
        </Group>
      ) : (
        <Group
          ref={contentGroupRef}
          x={layer.offsetX}
          y={layer.offsetY}
          draggable={isLayerMovable}
          onDragEnd={(e) => {
            const x = snapVal(e.target.x(), snapToGrid);
            const y = snapVal(e.target.y(), snapToGrid);
            e.target.x(x);
            e.target.y(y);
            onMoveLayer(layer.id, x, y);
          }}
        >
          {contentChildren}
        </Group>
      )}
    </Layer>
  );
}
