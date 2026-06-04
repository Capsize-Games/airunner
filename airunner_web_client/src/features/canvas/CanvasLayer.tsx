import { useRef, useEffect } from "react";
import { Group, Image as KonvaImage, Layer } from "react-konva";
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
  const groupRef = useRef<Konva.Group>(null);

  useEffect(() => {
    const group = groupRef.current;
    if (group) applyKonvaFilters(group, layer.filters);
  }, [layer.filters]);

  const isLayerMovable = activeTool === "move" && isActive;

  return (
    <Layer visible={layer.visible} opacity={layer.opacity}>
      <Group
        ref={groupRef}
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
      </Group>
    </Layer>
  );
}
