import Konva from "konva";
import type React from "react";
import type { ActiveGridArea } from "./useCanvasState";

/**
 * Export the canvas region covered by the Active Grid Area as base64 PNG.
 * Call this before triggering generation.
 */
export const exportRegion = (
  stageRef: React.RefObject<Konva.Stage>,
  area: ActiveGridArea,
  activeGridLayerRef: React.RefObject<Konva.Layer>,
  maskLayerRef: React.RefObject<Konva.Layer>,
): string => {
  activeGridLayerRef.current?.hide();
  maskLayerRef.current?.hide();

  const dataURL = stageRef.current!.toDataURL({
    x: area.x,
    y: area.y,
    width: area.width,
    height: area.height,
    pixelRatio: 1,
    mimeType: "image/png",
  });

  activeGridLayerRef.current?.show();
  maskLayerRef.current?.show();

  return dataURL.split(",")[1];
};

/**
 * Export the mask layer region as base64 PNG.
 * Used for inpainting masks.
 */
export const exportMaskLayer = (
  maskLayerRef: React.RefObject<Konva.Layer>,
  area: ActiveGridArea,
): string => {
  const dataURL = maskLayerRef.current!.toDataURL({
    x: area.x,
    y: area.y,
    width: area.width,
    height: area.height,
    pixelRatio: 1,
    mimeType: "image/png",
  });
  return dataURL.split(",")[1];
};

/** Snap a value to the nearest multiple of 8. */
export const snapTo8 = (val: number): number => Math.round(val / 8) * 8;

/** Clamp a value within [min, max]. */
export const clamp = (val: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, val));
