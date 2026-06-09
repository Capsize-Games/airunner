// ── Bucket (Flood) Fill Rendering Layer ───────────────────────────────
// The bucket fill tool modifies image data directly — no visual overlay
// is needed.  This component exists to satisfy the two-file-per-tool
// pattern and may be extended in the future.

import type { BucketRenderState } from "./useBucketTool";

export default function BucketLayer(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _props: BucketRenderState,
) {
  // No persistent visual overlay for bucket fill
  return null;
}
