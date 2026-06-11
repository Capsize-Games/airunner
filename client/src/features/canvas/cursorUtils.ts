import type { ActiveTool } from "./useCanvasState";

/**
 * Returns the CSS cursor string based on the active tool and whether
 * any layers exist.
 */
export function getCursor(
  tool: ActiveTool,
  hasLayers: boolean,
): string {
  if (!hasLayers) {
    return "not-allowed";
  }
  switch (tool) {
    case "select": return "crosshair";
    case "move":   return "grab";
    case "lasso":  return "crosshair";
    case "brush":
    case "eraser":
    case "mask":
    case "smudge":
    case "pipette": return "crosshair";
    case "text":    return "text";
    default:        return "default";
  }
}
