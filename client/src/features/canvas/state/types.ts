// ── Shared types for canvas state sub-hooks ────────────────────────────
import type { Dispatch, SetStateAction } from "react";
import type { CanvasState } from "../canvasTypes";

/** Setter pair passed from the orchestrating hook into every sub-hook. */
export interface CanvasSetters {
  setState: Dispatch<SetStateAction<CanvasState>>;
  /** Snapshots the previous state before returning the new one. */
  recordSnapshot: (prev: CanvasState) => CanvasState;
}
