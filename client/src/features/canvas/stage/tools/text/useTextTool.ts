// ── Text Tool Hook ─────────────────────────────────────────────────────
// Creates new text layers on click and manages HTML textarea overlay for
// editing (Konva.Text nodes are not natively keyboard-editable).
//
// Interaction model:
//   mousedown → addLayer, create Konva.Text, overlay HTML textarea
//   textarea input → auto-resize textarea to fit content
//   blur → commit text to layer, rename layer, remove textarea
//   escape → cancel editing, remove layer and textarea

import { useState, useRef, useCallback, useEffect } from "react";
import Konva from "konva";
import type { CanvasLayer, TextNodeData } from "../../../canvasTypes";

// ── Public types ──────────────────────────────────────────────────────────

export interface TextRenderState {
  /** Layer ID currently being edited (null = no active edit). */
  activeTextLayerId: string | null;
}

export interface UseTextToolReturn {
  renderState: TextRenderState;
  onMouseDown: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseMove: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
  onMouseUp: (e: Konva.KonvaEventObject<MouseEvent>) => boolean;
}

export interface TextToolProps {
  isActive: boolean;
  getCanvasPos: () => { x: number; y: number } | null;
  stageRef: React.RefObject<Konva.Stage>;
  textFont: string;
  textSize: number;
  textColor: string;
  layers: CanvasLayer[];
  addLayer: (name?: string, opacity?: number) => void;
  renameLayer: (id: string, name: string) => void;
  deleteLayer: (id: string) => void;
  setTextNode: (layerId: string, textNode: TextNodeData) => void;
  setActiveLayer: (id: string) => void;
}

// ── Constants ─────────────────────────────────────────────────────────────

const MAX_LAYER_NAME = 15;

const TEXTAREA_STYLE: Partial<CSSStyleDeclaration> = {
  position: "absolute",
  zIndex: "1000",
  minWidth: "20px",
  minHeight: "20px",
  padding: "2px 4px",
  margin: "0",
  border: "1.5px dashed rgba(111,168,255,0.7)",
  outline: "none",
  background: "rgba(0,0,0,0.6)",
  color: "#ffffff",
  fontFamily: "inherit",
  fontSize: "24px",
  lineHeight: "1.2",
  resize: "none",
  overflow: "hidden",
  whiteSpace: "pre-wrap",
  overflowWrap: "break-word",
  boxSizing: "border-box",
};

// ── Helpers ───────────────────────────────────────────────────────────────

function truncateName(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max) + "\u2026";
}

function fitTextarea(el: HTMLTextAreaElement): void {
  el.style.height = "auto";
  el.style.width = "auto";
  el.style.height = `${el.scrollHeight + 4}px`;
  el.style.width = `${Math.max(20, el.scrollWidth + 8)}px`;
}

/** The font/colour of a text node currently being edited. */
interface EditStyle {
  fontFamily: string;
  fontSize: number;
  fill: string;
}

// Reusable offscreen canvas for measuring text dimensions (hit-testing).
let measureCanvas: HTMLCanvasElement | null = null;

/** Measure the rendered size of a text block for click hit-testing. */
function measureText(
  text: string,
  fontFamily: string,
  fontSize: number,
): { width: number; height: number } {
  if (!measureCanvas) measureCanvas = document.createElement("canvas");
  const ctx = measureCanvas.getContext("2d");
  const lines = text.split("\n");
  if (!ctx) return { width: 0, height: lines.length * fontSize };
  ctx.font = `${fontSize}px ${fontFamily}`;
  let width = 0;
  for (const line of lines) {
    width = Math.max(width, ctx.measureText(line).width);
  }
  // Konva.Text default lineHeight is 1; pad slightly for a forgiving target.
  return { width, height: lines.length * fontSize * 1.2 };
}

// ── Main hook ─────────────────────────────────────────────────────────────

export function useTextTool({
  isActive,
  getCanvasPos,
  stageRef,
  textFont,
  textSize,
  textColor,
  layers,
  addLayer,
  renameLayer,
  deleteLayer,
  setTextNode,
  setActiveLayer,
}: TextToolProps): UseTextToolReturn {
  const [activeTextLayerId, setActiveTextLayerId] = useState<string | null>(
    null,
  );

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const editingLayerIdRef = useRef<string | null>(null);
  const editingLayerCreatedRef = useRef(false);
  const editingPosRef = useRef({ x: 0, y: 0 });
  // Style of the node currently being edited — tool defaults for brand-new
  // text, or the existing node's own style when editing in place.
  const editStyleRef = useRef<EditStyle>({
    fontFamily: textFont,
    fontSize: textSize,
    fill: textColor,
  });
  const settingsRef = useRef({ textFont, textSize, textColor });
  useEffect(() => {
    settingsRef.current = { textFont, textSize, textColor };
  }, [textFont, textSize, textColor]);
  // Keep latest layers in a ref so rAF callbacks see the updated value
  const layersRef = useRef(layers);
  useEffect(() => {
    layersRef.current = layers;
  }, [layers]);

  // ── Remove textarea from DOM ──────────────────────────────────────────
  const removeTextarea = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.remove();
      textareaRef.current = null;
    }
  }, []);

  // ── Commit editing ────────────────────────────────────────────────────
  const commit = useCallback(
    (layerId: string) => {
      const ta = textareaRef.current;
      if (!ta) return;

      const pos = editingPosRef.current;
      const s = editStyleRef.current;
      const text = ta.value;

      setTextNode(layerId, {
        text,
        x: pos.x,
        y: pos.y,
        fontFamily: s.fontFamily,
        fontSize: s.fontSize,
        fill: s.fill,
      });

      const name = text.trim()
        ? truncateName(text.trim(), MAX_LAYER_NAME)
        : "Text";
      renameLayer(layerId, name);

      removeTextarea();
      editingLayerIdRef.current = null;
      editingLayerCreatedRef.current = false;
      setActiveTextLayerId(null);
    },
    [setTextNode, renameLayer, removeTextarea],
  );

  // ── Cancel editing ────────────────────────────────────────────────────
  const cancel = useCallback(() => {
    const lid = editingLayerIdRef.current;
    if (lid && editingLayerCreatedRef.current) {
      deleteLayer(lid);
    }
    removeTextarea();
    editingLayerIdRef.current = null;
    editingLayerCreatedRef.current = false;
    setActiveTextLayerId(null);
  }, [deleteLayer, removeTextarea]);

  // ── Create textarea overlay ───────────────────────────────────────────
  const showTextarea = useCallback(
    (
      layerId: string,
      initialText: string,
      x: number,
      y: number,
      style: EditStyle,
    ) => {
      removeTextarea();

      const stage = stageRef.current;
      if (!stage) return;

      editStyleRef.current = style;
      const s = style;
      const container = stage.container();
      const parentEl = container.parentElement ?? document.body;

      const ta = document.createElement("textarea");
      ta.spellcheck = false;
      Object.assign(ta.style, TEXTAREA_STYLE);

      const absPos = stage.getAbsoluteTransform().point({ x, y });
      ta.style.left = `${absPos.x}px`;
      ta.style.top = `${absPos.y}px`;
      ta.style.fontSize = `${s.fontSize}px`;
      ta.style.fontFamily = s.fontFamily;
      ta.style.color = s.fill;
      ta.value = initialText;

      ta.addEventListener("input", () => {
        fitTextarea(ta);
        setTextNode(layerId, {
          text: ta.value,
          x,
          y,
          fontFamily: s.fontFamily,
          fontSize: s.fontSize,
          fill: s.fill,
        });
      });

      ta.addEventListener("blur", () => {
        commit(layerId);
      });

      ta.addEventListener("keydown", (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          ta.blur();
        }
      });

      parentEl.appendChild(ta);
      textareaRef.current = ta;
      editingLayerIdRef.current = layerId;
      editingPosRef.current = { x, y };

      requestAnimationFrame(() => {
        ta.focus();
        ta.select();
        fitTextarea(ta);
      });
    },
    [stageRef, setTextNode, commit, removeTextarea],
  );

  // ── Create new text layer and start editing ───────────────────────────
  const startNewText = useCallback(
    (x: number, y: number) => {
      const s = settingsRef.current;

      // Create a new layer
      addLayer("Text", 1);

      // The layers prop hasn't updated yet (React 18 batching).
      // Use rAF to run after the re-render.
      requestAnimationFrame(() => {
        const currentLayers = layersRef.current;
        // Now layers should have the new entry (last one)
        const newLayer = currentLayers[currentLayers.length - 1];
        // Guard: if no new layer appeared (edge case), skip
        if (!newLayer || newLayer.name !== "Text") {
          // Fallback: look for any layer without a textNode
          const candidate = [...currentLayers]
            .reverse()
            .find((l: CanvasLayer) => !l.textNode);
          if (candidate) {
            setTextNode(candidate.id, {
              text: "",
              x,
              y,
              fontFamily: s.textFont,
              fontSize: s.textSize,
              fill: s.textColor,
            });
            editingLayerCreatedRef.current = false;
            setActiveTextLayerId(candidate.id);
            showTextarea(candidate.id, "", x, y, {
              fontFamily: s.textFont,
              fontSize: s.textSize,
              fill: s.textColor,
            });
          }
          return;
        }

        setTextNode(newLayer.id, {
          text: "",
          x,
          y,
          fontFamily: s.textFont,
          fontSize: s.textSize,
          fill: s.textColor,
        });
        editingLayerCreatedRef.current = true;
        setActiveTextLayerId(newLayer.id);
        showTextarea(newLayer.id, "", x, y, {
          fontFamily: s.textFont,
          fontSize: s.textSize,
          fill: s.textColor,
        });

        // Batch draw the stage to show the new layer
        stageRef.current?.batchDraw();
      });
    },
    [
      addLayer,
      setTextNode,
      showTextarea,
      stageRef,
    ],
  );

  // ── Edit an existing text node in place ───────────────────────────────
  const editExistingText = useCallback(
    (layer: CanvasLayer) => {
      const node = layer.textNode;
      if (!node) return;
      setActiveLayer(layer.id);
      // Editing an existing layer — never delete it on cancel.
      editingLayerCreatedRef.current = false;
      setActiveTextLayerId(layer.id);
      showTextarea(layer.id, node.text, node.x, node.y, {
        fontFamily: node.fontFamily,
        fontSize: node.fontSize,
        fill: node.fill,
      });
    },
    [setActiveLayer, showTextarea],
  );

  // ── Find the topmost text node under a document-space point ───────────
  const findTextLayerAt = useCallback(
    (x: number, y: number): CanvasLayer | null => {
      const ls = layersRef.current;
      // Later layers render on top → search from the end.
      for (let i = ls.length - 1; i >= 0; i--) {
        const l = ls[i];
        if (!l.visible || !l.textNode || !l.textNode.text) continue;
        const { width, height } = measureText(
          l.textNode.text,
          l.textNode.fontFamily,
          l.textNode.fontSize,
        );
        const nx = l.offsetX + l.textNode.x;
        const ny = l.offsetY + l.textNode.y;
        const pad = 4;
        if (
          x >= nx - pad && x <= nx + width + pad &&
          y >= ny - pad && y <= ny + height + pad
        ) {
          return l;
        }
      }
      return null;
    },
    [],
  );

  // ── Reset when deactivated ────────────────────────────────────────────
  useEffect(() => {
    if (!isActive) {
      if (textareaRef.current && editingLayerIdRef.current) {
        const ta = textareaRef.current;
        if (ta.value.trim()) {
          commit(editingLayerIdRef.current);
        } else {
          cancel();
        }
      }
    }
  }, [isActive, commit, cancel]);

  // ── Global pointerup listener ─────────────────────────────────────────
  useEffect(() => {
    const onGlobalUp = () => {
      // Text commits on textarea blur — nothing to do.
    };
    window.addEventListener("pointerup", onGlobalUp);
    window.addEventListener("mouseup", onGlobalUp);
    return () => {
      window.removeEventListener("pointerup", onGlobalUp);
      window.removeEventListener("mouseup", onGlobalUp);
    };
  }, []);

  // ── Mouse handlers ────────────────────────────────────────────────────

  const onMouseDown = useCallback(
    (e: Konva.KonvaEventObject<MouseEvent>): boolean => {
      if (!isActive || e.evt.button !== 0) return false;

      // If already editing, commit current text first
      if (textareaRef.current && editingLayerIdRef.current) {
        const ta = textareaRef.current;
        if (ta.value.trim()) {
          commit(editingLayerIdRef.current);
        } else {
          cancel();
        }
      }

      const pos = getCanvasPos();
      if (!pos) return true;

      // Clicking on existing text edits it in place; otherwise start new text.
      const existing = findTextLayerAt(pos.x, pos.y);
      if (existing) {
        editExistingText(existing);
      } else {
        startNewText(pos.x, pos.y);
      }
      return true;
    },
    [isActive, getCanvasPos, commit, cancel, startNewText, findTextLayerAt, editExistingText],
  );

  const onMouseMove = useCallback((): boolean => false, []);

  const onMouseUp = useCallback((): boolean => false, []);

  return {
    renderState: { activeTextLayerId },
    onMouseDown,
    onMouseMove,
    onMouseUp,
  };
}
