import { useRef, useState, useCallback, useEffect } from "react";
import Konva from "konva";
import {
  useCanvasContext,
  useCanvasDocument,
  useCanvasSync,
} from "../../features/canvas";
import type { CanvasStageHandle } from "../../features/canvas/CanvasStage";
import CanvasStage from "../../features/canvas/CanvasStage";
import ToolBar, { type ToolbarDock } from "../../features/canvas/ToolBar";
import CanvasSettingsModal from "../../features/canvas/CanvasSettingsModal";
import ImageDropModal, {
  type DropResizeMode,
  fitDimensions,
} from "../../features/canvas/ImageDropModal";
import CanvasLayersSidebar from "../../features/canvas/CanvasLayersSidebar";
import CanvasStatusBar from "./canvas/CanvasStatusBar";
import ArtPromptPanel from "./ArtPromptPanel";
import ArtModelPanel from "./ArtModelPanel";
import LucideIcon from "../shared/LucideIcon";
import { useCanvasImageDrop } from "./canvas/useCanvasImageDrop";

export default function CanvasPanel() {
  const canvas = useCanvasContext();

  const stageRef = useRef<Konva.Stage>(null!) as React.RefObject<Konva.Stage>;
  const gridLayerRef = useRef<Konva.Layer>(null!) as React.RefObject<Konva.Layer>;
  const maskLayerRef = useRef<Konva.Layer>(null!) as React.RefObject<Konva.Layer>;
  const canvasHandleRef = useRef<CanvasStageHandle>(null);

  const [showGrid, setShowGrid] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [gridLocked, setGridLocked] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showNewDocModal, setShowNewDocModal] = useState(false);
  const [showLayers, setShowLayers] = useState(() => {
    try {
      return localStorage.getItem("canvas_show_layers") !== "false";
    } catch {
      return true;
    }
  });
  const [showArtPanel, setShowArtPanel] = useState(() => {
    try {
      return localStorage.getItem("canvas_show_art_panel") !== "false";
    } catch {
      return true;
    }
  });

  const [artPromptW, setArtPromptW] = useState(() => {
    try {
      const v = localStorage.getItem("canvas_art_prompt_w");
      return v !== null ? Number(v) : 260;
    } catch {
      return 260;
    }
  });
  const artPromptDrag = useRef(false);
  const artPromptStartX = useRef(0);
  const artPromptStartW = useRef(0);

  const handleArtPromptResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    artPromptDrag.current = true;
    artPromptStartX.current = e.clientX;
    artPromptStartW.current = artPromptW;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "";

    const onMove = (ev: MouseEvent) => {
      if (!artPromptDrag.current) return;
      const delta = ev.clientX - artPromptStartX.current;
      const newW = Math.max(180, Math.min(500, artPromptStartW.current - delta));
      setArtPromptW(newW);
    };

    const onUp = () => {
      artPromptDrag.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [artPromptW]);

  const [showArtModelSettings, setShowArtModelSettings] = useState(() => {
    try {
      return localStorage.getItem("canvas_show_art_model_settings") !== "false";
    } catch {
      return true;
    }
  });
  const [artModelSettingsH, setArtModelSettingsH] = useState(() => {
    try {
      const v = localStorage.getItem("canvas_art_model_settings_h");
      return v !== null ? Number(v) : 200;
    } catch {
      return 200;
    }
  });
  const artModelSettingsDrag = useRef(false);
  const artModelSettingsStartY = useRef(0);
  const artModelSettingsStartH = useRef(0);

  const handleArtModelSettingsResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    artModelSettingsDrag.current = true;
    artModelSettingsStartY.current = e.clientY;
    artModelSettingsStartH.current = artModelSettingsH;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "";

    const onMove = (ev: MouseEvent) => {
      if (!artModelSettingsDrag.current) return;
      const delta = ev.clientY - artModelSettingsStartY.current;
      const parent = (ev.target as HTMLElement).closest(
        "[data-art-panel]",
      ) as HTMLElement | null;
      const maxH = parent ? parent.clientHeight - 100 : 600;
      const newH = Math.max(120, Math.min(maxH, artModelSettingsStartH.current - delta));
      setArtModelSettingsH(newH);
    };

    const onUp = () => {
      artModelSettingsDrag.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [artModelSettingsH]);

  const [dock, setDock] = useState<ToolbarDock>(() =>
    (localStorage.getItem("canvas_toolbar_dock") as ToolbarDock | null) ?? "top",
  );

  const handleSetDock = useCallback((d: ToolbarDock) => {
    setDock(d);
    localStorage.setItem("canvas_toolbar_dock", d);
  }, []);

  // WebSocket sync for instant canvas persistence.
  const canvasSync = useCanvasSync({
    onDocument: (json) => {
      if (json) canvas.loadFromJSON(json);
    },
  });

  // Use persistable state (no history) for the backend — history is local-only.
  const documentString = JSON.stringify(canvas.getPersistableState());
  // Track whether the content actually differs from what was last saved.
  const [lastSavedDigest, setLastSavedDigest] = useState<string | null>(null);
  const currentDigest = documentString;
  const isDirty = currentDigest !== lastSavedDigest;

  const { isLoaded } = useCanvasDocument({
    documentString,
    onLoad: canvas.loadFromJSON,
    wsSend: canvasSync.send,
    isDirty,
    onSaved: () => setLastSavedDigest(currentDigest),
  });

  // ── Image drop handling ────────────────────────────────────────────────────

  const {
    pendingDrop,
    showDropModal,
    setShowDropModal,
    handleDragOver,
    handleDrop,
    queueDrop,
    useCanvasPlaceImage,
  } = useCanvasImageDrop(stageRef);

  // Listen for the "canvas-place-image" event fired by ServerImageRow
  useCanvasPlaceImage(queueDrop);

  const handleDropConfirm = useCallback(
    (mode: DropResizeMode) => {
      if (!pendingDrop) return;
      const { base64, x, y, naturalW, naturalH } = pendingDrop;
      let w = naturalW;
      let h = naturalH;
      if (mode === "fit-grid") {
        const fit = fitDimensions(
          naturalW,
          naturalH,
          canvas.activeGridArea.width,
          canvas.activeGridArea.height,
        );
        w = fit.w;
        h = fit.h;
      } else if (mode === "fit-canvas") {
        const fit = fitDimensions(
          naturalW,
          naturalH,
          canvas.documentWidth,
          canvas.documentHeight,
        );
        w = fit.w;
        h = fit.h;
      }
      canvas.placeImageOnNewLayer(
        base64,
        Math.max(0, x - w / 2),
        Math.max(0, y - h / 2),
        w,
        h,
      );
    },
    [pendingDrop, canvas],
  );

  // ── New document ──────────────────────────────────────────────────────────

  const handleNewDocument = useCallback(() => {
    setShowNewDocModal(true);
  }, []);

  const handleNewDocumentConfirm = useCallback(
    (w: number, h: number, bg: string) => {
      canvas.resetDocument();
      canvas.setDocumentSize(w, h);
      canvas.setDocumentBgColor(bg);
    },
    [canvas],
  );

  // ── Canvas settings ───────────────────────────────────────────────────────

  const handleApplySettings = useCallback(
    (w: number, h: number, bg: string) => {
      canvas.setDocumentSize(w, h);
      canvas.setDocumentBgColor(bg);
    },
    [canvas],
  );

  useEffect(() => {
    try { localStorage.setItem("canvas_show_layers", String(showLayers)); } catch { /* */ }
  }, [showLayers]);
  useEffect(() => {
    try { localStorage.setItem("canvas_show_art_panel", String(showArtPanel)); } catch { /* */ }
  }, [showArtPanel]);
  useEffect(() => {
    try { localStorage.setItem("canvas_show_art_model_settings", String(showArtModelSettings)); } catch { /* */ }
  }, [showArtModelSettings]);
  useEffect(() => {
    try { localStorage.setItem("canvas_art_model_settings_h", String(artModelSettingsH)); } catch { /* */ }
  }, [artModelSettingsH]);
  useEffect(() => {
    try { localStorage.setItem("canvas_art_prompt_w", String(artPromptW)); } catch { /* */ }
  }, [artPromptW]);

  if (!isLoaded) {
    return (
      <div className="canvas-panel d-flex align-items-center justify-content-center h-100">
        <div
          className="spinner-border spinner-border-sm"
          role="status"
          style={{ color: "var(--theme-text-secondary)" }}
        />
      </div>
    );
  }

  const sharedToolbarProps = {
    activeTool: canvas.activeTool,
    brushSize: canvas.brushSize,
    brushColor: canvas.brushColor,
    showGrid,
    snapToGrid: canvas.snapToGrid,
    zoom,
    activeGridArea: canvas.activeGridArea,
    gridLocked,
    onSetActiveTool: canvas.setActiveTool,
    onSetBrushSize: canvas.setBrushSize,
    onSetBrushColor: canvas.setBrushColor,
    onToggleGrid: () => setShowGrid((v) => !v),
    onToggleSnap: () => canvas.setSnapToGrid(!canvas.snapToGrid),
    onZoomIn: () => canvasHandleRef.current?.zoomIn(),
    onZoomOut: () => canvasHandleRef.current?.zoomOut(),
    onZoomReset: () => canvasHandleRef.current?.zoomReset(),
    onCenterView: () => canvasHandleRef.current?.centerView(),
    onSetGridArea: canvas.setActiveGridArea,
    onToggleGridLock: () => setGridLocked((v) => !v),
    onOpenSettings: () => setShowSettings(true),
    onSetDock: handleSetDock,
    onUndo: canvas.undo,
    onRedo: canvas.redo,
    onNewDocument: handleNewDocument,
    onClearMask: canvas.clearMask,
    hasMaskStrokes: canvas.maskStrokes.length > 0,
    showLayers,
    onToggleLayers: () => setShowLayers((v) => !v),
    showArtPanel,
    onToggleArtPanel: () => setShowArtPanel((v) => !v),
  };

  return (
    <div
      className="canvas-panel d-flex h-100 overflow-hidden flex-column"
      style={{ background: "#0a0a0f" }}
    >
      {dock === "top" && <ToolBar {...sharedToolbarProps} dock="top" />}

      {/* Canvas viewport + layers sidebar */}
      <div
        className="flex-grow-1 d-flex flex-column overflow-hidden"
        style={{ minWidth: 0, minHeight: 0 }}
      >
        <div
          className="flex-grow-1 d-flex flex-row overflow-hidden"
          style={{ minHeight: 0 }}
        >
          <div
            className="flex-grow-1 overflow-hidden"
            style={{ background: "#0a0a0f", position: "relative" }}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <CanvasStage
              ref={canvasHandleRef}
              documentWidth={canvas.documentWidth}
              documentHeight={canvas.documentHeight}
              documentBgColor={canvas.documentBgColor}
              layers={canvas.layers}
              activeLayerId={canvas.activeLayerId}
              activeGridArea={canvas.activeGridArea}
              activeTool={canvas.activeTool}
              brushSize={canvas.brushSize}
              brushColor={canvas.brushColor}
              maskStrokes={canvas.maskStrokes}
              showGrid={showGrid}
              snapToGrid={canvas.snapToGrid}
              onAddStroke={canvas.addStroke}
              onMoveImage={canvas.moveImage}
              onMoveLayer={canvas.moveLayer}
              onAddMaskStroke={canvas.addMaskStroke}
              setActiveGridArea={canvas.setActiveGridArea}
              onUndo={canvas.undo}
              onRedo={canvas.redo}
              setActiveTool={canvas.setActiveTool}
              onZoomChange={setZoom}
              gridLayerRef={gridLayerRef}
              maskLayerRef={maskLayerRef}
              stageRef={stageRef}
            />
          </div>
          {showLayers && <CanvasLayersSidebar />}
          {showArtPanel && (
            <div
              style={{
                width: artPromptW,
                flexShrink: 0,
                display: "flex",
                flexDirection: "row",
                overflow: "hidden",
              }}
            >
              <div
                onMouseDown={handleArtPromptResize}
                style={{
                  width: 4,
                  cursor: "col-resize",
                  flexShrink: 0,
                  background: "transparent",
                  transition: "background 0.15s",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLDivElement).style.background =
                    "rgba(99,153,255,0.3)";
                }}
                onMouseLeave={(e) => {
                  if (!artPromptDrag.current) {
                    (e.currentTarget as HTMLDivElement).style.background =
                      "transparent";
                  }
                }}
              />
              <div
                data-art-panel
                style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}
              >
                <div className="art-prompt-panel" style={{ flex: 1, overflow: "auto" }}>
                  <ArtPromptPanel
                    showArtModelSettings={showArtModelSettings}
                    onToggleArtModelSettings={() => setShowArtModelSettings((v) => !v)}
                  />
                </div>
                {showArtModelSettings && (
                  <div
                    onMouseDown={handleArtModelSettingsResize}
                    style={{
                      height: 4,
                      cursor: "row-resize",
                      flexShrink: 0,
                      background: "transparent",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLDivElement).style.background =
                        "rgba(99,153,255,0.3)";
                    }}
                    onMouseLeave={(e) => {
                      if (!artModelSettingsDrag.current) {
                        (e.currentTarget as HTMLDivElement).style.background =
                          "transparent";
                      }
                    }}
                  />
                )}
                {showArtModelSettings ? (
                  <div style={{ overflow: "auto", height: artModelSettingsH, flexShrink: 0 }}>
                    <ArtModelPanel />
                  </div>
                ) : (
                  <div
                    onClick={() => setShowArtModelSettings(true)}
                    style={{
                      borderTop: "1px solid rgba(255,255,255,0.07)",
                      padding: "6px 8px",
                      flexShrink: 0,
                      fontSize: 11,
                      color: "rgba(255,255,255,0.35)",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 6,
                      cursor: "pointer",
                    }}
                  >
                    <LucideIcon name="sparkles" size={12} />
                    <span style={{
                      flex: 1, minWidth: 0,
                      lineHeight: 1.5,
                      whiteSpace: "pre-line",
                    }}>
                      {(() => {
                        const ls = (k: string, fb = "") => {
                          try { return localStorage.getItem(k) || fb; } catch { return fb; }
                        };
                        const v = ls("airunner_art_version");
                        const m = ls("airunner_art_model");
                        const short = m ? m.split(/[/\\]/).pop() || m : "";
                        const s = ls("n_samples", "1");
                        const b = ls("images_per_batch", "1");
                        const st = ls("steps", "20");
                        const c = ls("cfg_scale", "7.5");
                        if (v && short) {
                          return `${v} · ${short}\nSamples: ${s} · Batch: ${b} · Steps: ${st} · CFG: ${c}`;
                        }
                        return "No model selected";
                      })()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Status bar */}
        <CanvasStatusBar
          documentWidth={canvas.documentWidth}
          documentHeight={canvas.documentHeight}
          zoom={zoom}
          gridWidth={canvas.activeGridArea.width}
          gridHeight={canvas.activeGridArea.height}
          activeLayer={canvas.activeLayer}
          connected={canvasSync.connected}
        />
      </div>

      {dock === "bottom" && (
        <ToolBar {...sharedToolbarProps} dock="bottom" />
      )}

      {/* Modals */}
      <CanvasSettingsModal
        show={showSettings}
        documentWidth={canvas.documentWidth}
        documentHeight={canvas.documentHeight}
        documentBgColor={canvas.documentBgColor}
        onApply={handleApplySettings}
        onHide={() => setShowSettings(false)}
      />
      <CanvasSettingsModal
        show={showNewDocModal}
        newDocumentMode
        documentWidth={canvas.documentWidth}
        documentHeight={canvas.documentHeight}
        documentBgColor={canvas.documentBgColor}
        onApply={handleNewDocumentConfirm}
        onHide={() => setShowNewDocModal(false)}
      />

      <ImageDropModal
        show={showDropModal}
        naturalW={pendingDrop?.naturalW ?? 0}
        naturalH={pendingDrop?.naturalH ?? 0}
        gridW={canvas.activeGridArea.width}
        gridH={canvas.activeGridArea.height}
        canvasW={canvas.documentWidth}
        canvasH={canvas.documentHeight}
        onConfirm={handleDropConfirm}
        onHide={() => setShowDropModal(false)}
      />
    </div>
  );
}
