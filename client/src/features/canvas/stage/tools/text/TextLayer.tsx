// ── Text Tool Rendering Layer ──────────────────────────────────────────
// All Konva.Text nodes are rendered inline inside CanvasLayerRenderer
// via the contentChildren block.  This component exists to satisfy the
// two-file-per-tool pattern and may render additional text-tool chrome
// (e.g. selection cursor, active edit indicator) in the future.

import type { TextRenderState } from "./useTextTool";

export default function TextLayer(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _props: TextRenderState,
) {
  // Konva.Text nodes live inside CanvasLayerRenderer per-layer.
  // No separate overlay needed here.
  return null;
}
