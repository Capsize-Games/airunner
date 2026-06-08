import { useRef, useCallback } from "react";
import Konva from "konva";
import type { LiveStrokeMessage } from "./canvasSyncTypes";

// ── Types ──────────────────────────────────────────────────────────────

export interface GhostStroke {
  layerId: string;
  strokeId: string;
  tool: "brush" | "eraser";
  color: string;
  strokeWidth: number;
  points: number[];
}

export interface UseGhostStrokesReturn {
  /** Append a delta to the ghost stroke for the given session. */
  applyLiveDelta: (msg: LiveStrokeMessage) => void;
  /** Remove the ghost stroke for a session (on stroke:end or new document). */
  clearGhost: (sessionId: string) => void;
  /** Clear all ghost strokes (e.g. on full document load). */
  clearAll: () => void;
  /** Ref to attach to the ghost Konva <Layer>. Managed imperatively. */
  ghostLayerRef: React.RefObject<Konva.Layer | null>;
}

// ── Module-level ghost map (outside React state) ──────────────────────

const ghostStrokes = new Map<string, GhostStroke>();

// ── Hook ──────────────────────────────────────────────────────────────

export function useGhostStrokes(): UseGhostStrokesReturn {
  const ghostLayerRef = useRef<Konva.Layer | null>(null);

  /** Sync the ghost map into Konva Lines on the ghost layer. */
  const renderGhosts = useCallback(() => {
    const layer = ghostLayerRef.current;
    if (!layer) return;

    // Recreate all ghost lines imperatively so we avoid stale remove/destroy
    // order issues with Konva's internal node tracking.
    layer.destroyChildren();

    for (const [, ghost] of ghostStrokes) {
      if (ghost.points.length < 4) continue;
      const line = new Konva.Line({
        points: ghost.points,
        stroke: ghost.tool === "eraser" ? "#000000" : ghost.color,
        strokeWidth: ghost.strokeWidth,
        lineCap: "round",
        lineJoin: "round",
        globalCompositeOperation:
          ghost.tool === "eraser" ? "destination-out" : "source-over",
        listening: false,
      });
      layer.add(line);
    }

    layer.batchDraw();
  }, []);

  const applyLiveDelta = useCallback(
    (msg: LiveStrokeMessage) => {
      let ghost = ghostStrokes.get(msg.sessionId);
      if (!ghost || ghost.strokeId !== msg.strokeId) {
        // New stroke from this session — start fresh.
        ghost = {
          layerId: msg.layerId,
          strokeId: msg.strokeId,
          tool: msg.tool,
          color: msg.color,
          strokeWidth: msg.strokeWidth,
          points: [],
        };
        ghostStrokes.set(msg.sessionId, ghost);
      }
      // Append delta points.
      ghost.points.push(...msg.delta);
      renderGhosts();
    },
    [renderGhosts],
  );

  const clearGhost = useCallback(
    (sessionId: string) => {
      ghostStrokes.delete(sessionId);
      renderGhosts();
    },
    [renderGhosts],
  );

  const clearAll = useCallback(() => {
    ghostStrokes.clear();
    renderGhosts();
  }, [renderGhosts]);

  return { applyLiveDelta, clearGhost, clearAll, ghostLayerRef };
}
