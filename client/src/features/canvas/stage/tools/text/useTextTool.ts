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
}: TextToolProps): UseTextToolReturn {
  const [activeTextLayerId, setActiveTextLayerId] = useState<string | null>(
    null,
  );

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const editingLayerIdRef = useRef<string | null>(null);
  const editingLayerCreatedRef = useRef(false);
  const editingPosRef = useRef({ x: 0, y: 0 });
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
      const s = settingsRef.current;
      const text = ta.value;

      setTextNode(layerId, {
        text,
        x: pos.x,
        y: pos.y,
        fontFamily: s.textFont,
        fontSize: s.textSize,
        fill: s.textColor,
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
    ) => {
      removeTextarea();

      const stage = stageRef.current;
      if (!stage) return;

      const s = settingsRef.current;
      const container = stage.container();
      const parentEl = container.parentElement ?? document.body;

      const ta = document.createElement("textarea");
      ta.spellcheck = false;
      Object.assign(ta.style, TEXTAREA_STYLE);

      const absPos = stage.getAbsoluteTransform().point({ x, y });
      ta.style.left = `${absPos.x}px`;
      ta.style.top = `${absPos.y}px`;
      ta.style.fontSize = `${s.textSize}px`;
      ta.style.fontFamily = s.textFont;
      ta.style.color = s.textColor;
      ta.value = initialText;

      ta.addEventListener("input", () => {
        fitTextarea(ta);
        setTextNode(layerId, {
          text: ta.value,
          x,
          y,
          fontFamily: s.textFont,
          fontSize: s.textSize,
          fill: s.textColor,
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
            showTextarea(candidate.id, "", x, y);
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
        showTextarea(newLayer.id, "", x, y);

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

      startNewText(pos.x, pos.y);
      return true;
    },
    [isActive, getCanvasPos, commit, cancel, startNewText],
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
