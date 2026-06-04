import type { ActiveTool } from "./useCanvasState";

/**
 * Returns the CSS cursor string based on the active tool and whether
 * any layers exist.
 */
export function getCursor(
  tool: ActiveTool,
  hasLayers: boolean,
): string {
  if (!hasLayers &&
    (tool === "brush" || tool === "eraser" || tool === "mask")
  ) {
    return "not-allowed";
  }
  switch (tool) {
    case "select": return "crosshair";
    case "move":   return "grab";
    case "brush":
    case "eraser":
    case "mask":   return "crosshair";
  }
}
