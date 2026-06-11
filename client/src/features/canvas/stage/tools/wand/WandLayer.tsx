// ── Fuzzy Select (Magic Wand) Rendering Layer ─────────────────────────────
// The committed fuzzy-select boundary is now rendered by the shared,
// tool-independent SelectionOverlay (so the selection persists across tool
// switches and drives the clipboard). The wand has no in-progress visual of
// its own, so this layer renders nothing — kept to satisfy the
// two-file-per-tool pattern.

import type { WandRenderState } from "./useWandTool";

export default function WandLayer(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _props: WandRenderState,
) {
  return null;
}
