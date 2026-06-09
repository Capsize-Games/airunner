// ── Pipette (Color Picker) Tool Rendering Layer ───────────────────────
// The pipette tool reads pixel color on click and updates global state —
// no separate visual overlay is needed.  This component exists to satisfy
// the two-file-per-tool pattern.

import type { PipetteRenderState } from "./usePipetteTool";

export default function PipetteLayer(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _props: PipetteRenderState,
) {
  // No visual overlay — color is sampled and applied atomically on click.
  return null;
}
