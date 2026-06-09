// ── Canvas Image Operations ─────────────────────────────────────────────
import { useCallback } from "react";
import type { CanvasLayer, ImageNode } from "../canvasTypes";
import {
  nextLayerId,
  nextImageId,
} from "../canvasStateUtils";
import type { CanvasSetters } from "./types";

export function images(
  { setState, recordSnapshot }: CanvasSetters,
) {
  const placeImageOnNewLayer = useCallback(
    (
      base64: string,
      x: number,
      y: number,
      width: number,
      height: number,
    ) => {
      setState((prev) => {
        const newLayerId = nextLayerId();
        const newImage: ImageNode = {
          id: nextImageId(),
          x,
          y,
          width,
          height,
          src: base64.startsWith("data:")
            ? base64
            : `data:image/png;base64,${base64}`,
        };
        const newLayer: CanvasLayer = {
          id: newLayerId,
          name: `Image ${prev.layers.length + 1}`,
          visible: true,
          opacity: 1,
          filters: [],
          images: [newImage],
          strokes: [],
          offsetX: 0,
          offsetY: 0,
          parentGroupId: null,
        };
        return recordSnapshot({
          ...prev,
          layers: [...prev.layers, newLayer],
          displayOrder: [...prev.displayOrder, newLayerId],
          activeLayerId: newLayerId,
          selectedLayerIds: [newLayerId],
        });
      });
    },
    [setState, recordSnapshot],
  );

  const placeImage = useCallback(
    (
      base64: string,
      x: number,
      y: number,
      width: number,
      height: number,
    ) => {
      setState((prev) => {
        const activeIdx = prev.layers.findIndex(
          (l) => l.id === prev.activeLayerId,
        );
        if (activeIdx === -1) return prev;
        const newImage: ImageNode = {
          id: nextImageId(),
          x,
          y,
          width,
          height,
          src: base64.startsWith("data:")
            ? base64
            : `data:image/png;base64,${base64}`,
        };
        const layers = prev.layers.map((l, i) =>
          i === activeIdx
            ? { ...l, images: [...l.images, newImage] }
            : l,
        );
        return recordSnapshot({ ...prev, layers });
      });
    },
    [setState, recordSnapshot],
  );

  const moveImage = useCallback(
    (
      layerId: string,
      imageId: string,
      x: number,
      y: number,
    ) => {
      setState((prev) =>
        recordSnapshot({
          ...prev,
          layers: prev.layers.map((l) =>
            l.id !== layerId
              ? l
              : {
                  ...l,
                  images: l.images.map((img) =>
                    img.id === imageId
                      ? { ...img, x, y }
                      : img,
                  ),
                },
          ),
        }),
      );
    },
    [setState, recordSnapshot],
  );

  return { placeImageOnNewLayer, placeImage, moveImage };
}
