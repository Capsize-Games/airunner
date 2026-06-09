import { useRef, useEffect, useLayoutEffect, useCallback } from "react";
import { Group, Image as KonvaImage, Layer, Line, Rect } from "react-konva";
import Konva from "konva";
import type { CanvasLayer as CanvasLayerType, StrokeNode, ActiveTool, MoveMode } from "./useCanvasState";
import DrawingLayer from "./DrawingLayer";

interface CanvasLayerProps {
  layer: CanvasLayerType;
  isActive: boolean;
  activeTool: ActiveTool;
  moveMode: MoveMode;
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

/** Cache bounds matching the clip rectangle. */
function clipCacheBounds(offsetX: number, offsetY: number, w: number, h: number) {
  return { x: -offsetX, y: -offsetY, width: w, height: h, pixelRatio: 1 };
}

export default function CanvasLayerRenderer({
  layer,
  isActive,
  activeTool,
  moveMode,
  brushSize,
  brushColor,
  snapToGrid,
  canvasWidth,
  canvasHeight,
  onStrokeComplete,
  onMoveImage,
  onMoveLayer,
}: CanvasLayerProps) {
  const layerRef = useRef<Konva.Layer>(null);
  const outerGroupRef = useRef<Konva.Group>(null);
  const contentGroupRef = useRef<Konva.Group>(null);
  const dragGroupRef = useRef<Konva.Group>(null);
  const maskGroupRef = useRef<Konva.Group>(null);
  // Ref to the inner clipped Group (hasMask: outerGroupRef, no-mask: contentGroupRef).
  const clippedGroupRef = useRef<Konva.Group | null>(null);
  const hasMask = Array.isArray(layer.maskStrokes);

  useEffect(() => {
    if (contentGroupRef.current) applyKonvaFilters(contentGroupRef.current, layer.filters);
  }, [layer.filters]);

  // Stage-level move tool handles both "pick" and "move-selected"
  // modes, so we disable the per-layer transparent overlay rect.
  const isLayerMovable = false;

  // ── Imperative Layer clip ─────────────────────────────────────────────
  // react-konva may not reliably pass clip props through to the native
  // Konva Layer node, so we set them directly via the ref.  The Layer
  // clip is fixed in Stage space — it never moves, which is why the
  // content slides underneath it during drag (the desired pan behavior).
  useLayoutEffect(() => {
    const l = layerRef.current;
    if (l) {
      l.clipX(0);
      l.clipY(0);
      l.clipWidth(canvasWidth);
      l.clipHeight(canvasHeight);
    }
  }, [canvasWidth, canvasHeight]);

  // ── mask compositing cache ─────────────────────────────────────────────
  useLayoutEffect(() => {
    if (!hasMask) return;
    const bounds = clipCacheBounds(
      layer.offsetX, layer.offsetY, canvasWidth, canvasHeight,
    );
    requestAnimationFrame(() => {
      const maskG = maskGroupRef.current;
      if (maskG) maskG.cache(bounds);
      const outerG = outerGroupRef.current;
      if (outerG) {
        outerG.cache(bounds);
        outerG.getLayer()?.batchDraw();
      }
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMask, layer.maskStrokes, layer.maskFill, layer.images, layer.strokes, layer.filters, layer.offsetX, layer.offsetY, canvasWidth, canvasHeight]);

  // ── manual drag for move tool ──────────────────────────────────────────
  // Konva's built-in draggable uses CSS transforms which bypass the
  // Group-level clip property during drag.  We use manual pointer events
  // to update position via group.x() / group.y() instead, and
  // dynamically shift the inner Group's clipX / clipY so the clip
  // window stays pinned at the Layer origin (0,0) while dragging.
  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const groupStart = useRef({ x: 0, y: 0 });

  const handleLayerPointerDown = useCallback(
    (e: Konva.KonvaEventObject<PointerEvent>) => {
      if (!isLayerMovable) return;
      // Only respond to left button — let middle/right button
      // events pass through to the Stage for panning.
      if (e.evt.button !== 0) return;
      e.evt.stopPropagation();
      e.evt.preventDefault();
      const group = dragGroupRef.current;
      if (!group) return;
      const stage = group.getStage();
      if (!stage) return;
      const pos = stage.getPointerPosition();
      if (!pos) return;

      isDragging.current = true;
      dragStart.current = { x: pos.x, y: pos.y };
      groupStart.current = { x: group.x(), y: group.y() };
    },
    [isLayerMovable],
  );

  // During drag we simultaneously update the outer Group's position
  // AND the inner Group's clip offsets.  Without the clip offset
  // adjustment the clip window would shift with the Group, showing
  // the same slice of content plus an empty gap — the user would
  // not see the content "pan" within the viewport.
  const handleLayerPointerMove = useCallback(
    (e: Konva.KonvaEventObject<PointerEvent>) => {
      if (!isDragging.current || !isLayerMovable) return;
      e.evt.stopPropagation();
      const group = dragGroupRef.current;
      if (!group) return;
      const stage = group.getStage();
      if (!stage) return;
      const pos = stage.getPointerPosition();
      if (!pos) return;
      const newX = groupStart.current.x + pos.x - dragStart.current.x;
      const newY = groupStart.current.y + pos.y - dragStart.current.y;
      group.x(newX);
      group.y(newY);

      // Counteract the Group's position change by shifting the
      // inner Group's clip in the opposite direction so the clip
      // stays fixed at (0,0) in Layer coordinates.
      const clipped = clippedGroupRef.current;
      if (clipped) {
        clipped.clipX(-newX);
        clipped.clipY(-newY);
      }

      group.getLayer()?.batchDraw();
    },
    [isLayerMovable],
  );

  const handleLayerPointerUp = useCallback(
    (e?: Konva.KonvaEventObject<PointerEvent>) => {
      if (!isDragging.current || !isLayerMovable) return;
      if (e) e.evt.stopPropagation();
      isDragging.current = false;
      const group = dragGroupRef.current;
      if (!group) return;
      const x = snapVal(group.x(), snapToGrid);
      const y = snapVal(group.y(), snapToGrid);
      group.x(x);
      group.y(y);
      group.getLayer()?.batchDraw();
      onMoveLayer(layer.id, x, y);
    },
    [isLayerMovable, snapToGrid, layer.id, onMoveLayer],
  );

  // Catch pointerup globally so layer dragging stops even when
  // the cursor leaves the canvas and releases outside.
  useEffect(() => {
    const onGlobalUp = () => handleLayerPointerUp();
    window.addEventListener("pointerup", onGlobalUp);
    return () =>
      window.removeEventListener("pointerup", onGlobalUp);
  }, [handleLayerPointerUp]);

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
        isActive={isActive}
      />
    </>
  );

  return (
    <Layer ref={layerRef} visible={layer.visible} opacity={layer.opacity}>
      {hasMask ? (
        <Group ref={dragGroupRef} x={layer.offsetX} y={layer.offsetY} name={"layer-drag-" + layer.id}>
          <Group
            ref={(node) => {
              outerGroupRef.current = node;
              clippedGroupRef.current = node;
            }}
            name={"layer-clip-" + layer.id}
            clipX={-layer.offsetX}
            clipY={-layer.offsetY}
            clipWidth={canvasWidth}
            clipHeight={canvasHeight}
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
          {isLayerMovable && (
            <Rect
              x={-layer.offsetX}
              y={-layer.offsetY}
              width={canvasWidth}
              height={canvasHeight}
              fill="transparent"
              listening={true}
              style={{ cursor: "grab" }}
              onPointerDown={handleLayerPointerDown}
              onPointerMove={handleLayerPointerMove}
              onPointerUp={handleLayerPointerUp}
            />
          )}
        </Group>
      ) : (
        <Group ref={dragGroupRef} x={layer.offsetX} y={layer.offsetY} name={"layer-drag-" + layer.id}>
          <Group
            ref={(node) => {
              contentGroupRef.current = node;
              clippedGroupRef.current = node;
            }}
            name={"layer-clip-" + layer.id}
            clipX={-layer.offsetX}
            clipY={-layer.offsetY}
            clipWidth={canvasWidth}
            clipHeight={canvasHeight}
          >
            {contentChildren}
          </Group>
          {isLayerMovable && (
            <Rect
              x={-layer.offsetX}
              y={-layer.offsetY}
              width={canvasWidth}
              height={canvasHeight}
              fill="transparent"
              listening={true}
              style={{ cursor: "grab" }}
              onPointerDown={handleLayerPointerDown}
              onPointerMove={handleLayerPointerMove}
              onPointerUp={handleLayerPointerUp}
            />
          )}
        </Group>
      )}
    </Layer>
  );
}
