// ── Smudge Tool Rendering Layer ─────────────────────────────────────────
// The smudge tool updates the target Konva.Image directly during
// mousemove for real-time visual feedback — no separate overlay is
// needed.  This component exists to satisfy the two-file-per-tool
// pattern and may be extended in the future.

import type { SmudgeRenderState } from "./useSmudgeTool";

export default function SmudgeLayer(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _props: SmudgeRenderState,
) {
  // No visual overlay — pixel updates go direct to the Konva.Image
  return null;
}
