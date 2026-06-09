import { useRef, useState, useCallback, useEffect } from "react";
import Konva from "konva";
import { RefreshCcw, RefreshCcwDot } from "lucide-react";
import {
  useCanvasContext,
  useCanvasDocument,
  useCanvasSync,
} from "../../features/canvas";
import { useGhostStrokes } from "../../features/canvas/useGhostStrokes";
import type { CanvasStageHandle } from "../../features/canvas/CanvasStage";
import CanvasStage from "../../features/canvas/CanvasStage";
import CanvasSettingsModal from "../../features/canvas/CanvasSettingsModal";
import ImageDropModal, {
  type DropResizeMode,
  fitDimensions,
} from "../../features/canvas/ImageDropModal";
import CanvasAssetsSidebar from "../../features/canvas/CanvasAssetsSidebar";
import CanvasStatusBar from "./canvas/CanvasStatusBar";
import ArtPromptPanel from "./ArtPromptPanel";
import CanvasToolPanel from "../../features/canvas/CanvasToolPanel";
import BrushControls from "../../features/canvas/sidebar/BrushControls";
import MoveControls from "../../features/canvas/sidebar/MoveControls";
import LassoControls from "../../features/canvas/sidebar/LassoControls";
import WandControls from "../../features/canvas/sidebar/WandControls";
import CropControls from "../../features/canvas/sidebar/CropControls";
import BucketControls from "../../features/canvas/sidebar/BucketControls";
import SmudgeControls from "../../features/canvas/sidebar/SmudgeControls";
import PipetteControls from "../../features/canvas/sidebar/PipetteControls";
import ZoomControls from "../../features/canvas/sidebar/ZoomControls";
import TextControls from "../../features/canvas/sidebar/TextControls";
import GridControls from "../../features/canvas/sidebar/GridControls";
import { useCanvasImageDrop } from "./canvas/useCanvasImageDrop";

const LS_LEFT_W = "airunner_left_panel_w";
const LEFT_PANEL_MIN = 220;
const LEFT_PANEL_MAX = 560;

const TOOL_LABELS: Record<string, string> = {
  move:    "Move",
  select:  "Selection",
  lasso:   "Free Select",
  wand:    "Fuzzy Select",
  crop:    "Crop",
  bucket:  "Bucket Fill",
  smudge:  "Smudge",
  text:    "Text",
  pipette: "Color Picker",
  zoom:    "Zoom",
  brush:   "Brush",
  eraser:  "Eraser",
  grid:    "Grid",
};

let leftPanelDrag: { startX: number; startW: number; setW: (w: number) => void } | null = null;
if (typeof window !== "undefined") {
  window.addEventListener("mousemove", (e: MouseEvent) => {
    if (!leftPanelDrag) return;
    const delta = e.clientX - leftPanelDrag.startX;
    leftPanelDrag.setW(Math.max(LEFT_PANEL_MIN, Math.min(LEFT_PANEL_MAX, leftPanelDrag.startW + delta)));
  });
  window.addEventListener("mouseup", () => {
    if (!leftPanelDrag) return;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    leftPanelDrag = null;
  });
}

const resetBtnStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "center",
  width: 28, height: 26, padding: 0,
  background: "transparent", border: "none",
  borderRadius: 4, cursor: "pointer",
  color: "rgba(255,255,255,0.35)",
  transition: "background 0.1s, color 0.1s",
};

export default function CanvasPanel() {
  const canvas = useCanvasContext();

  const stageRef = useRef<Konva.Stage>(null!) as React.RefObject<Konva.Stage>;
  const gridLayerRef = useRef<Konva.Layer>(null!) as React.RefObject<Konva.Layer>;
  const maskLayerRef = useRef<Konva.Layer>(null!) as React.RefObject<Konva.Layer>;
  const canvasHandleRef = useRef<CanvasStageHandle>(null);

  const ghostStrokes = useGhostStrokes();

  const [zoom, setZoom] = useState(1);
  const [isFitToView, setIsFitToView] = useState(() => {
    try { return localStorage.getItem("canvas_fit_to_view") !== "false"; } catch { return true; }
  });
  const [isCenterView, setIsCenterView] = useState(() => {
    try { return localStorage.getItem("canvas_center_view") === "true"; } catch { return false; }
  });
  const [assetTab, setAssetTab] = useState<"layers" | "images" | null>(() => {
    try {
      const v = localStorage.getItem("canvas_asset_tab");
      if (v === "layers" || v === "images") return v;
      return localStorage.getItem("canvas_show_assets") !== "false" ? "layers" : null;
    } catch { return "layers"; }
  });
  const [gridLocked] = useState(() => {
    try { return localStorage.getItem("canvas_grid_locked") === "true"; } catch { return false; }
  });
  const [showSettings, setShowSettings] = useState(false);
  const [showNewDocModal, setShowNewDocModal] = useState(false);
  const [showImagePrompt, setShowImagePrompt] = useState(false);
  const [leftPanelW, setLeftPanelW] = useState(() => {
    try { const v = localStorage.getItem(LS_LEFT_W); return v ? Number(v) : 300; } catch { return 300; }
  });

  const canvasSync = useCanvasSync({
    onDocument: (json) => {
      if (json) {
        ghostStrokes.clearAll();
        canvas.loadFromJSON(json);
      }
    },
    onLiveStroke: ghostStrokes.applyLiveDelta,
    onStrokeEnd: (msg) => ghostStrokes.clearGhost(msg.sessionId),
  });

  const documentString = JSON.stringify(canvas.getPersistableState());
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

  const {
    pendingDrop,
    showDropModal,
    setShowDropModal,
    handleDragOver,
    handleDrop,
    queueDrop,
    viewportCenter,
    useCanvasPlaceImage,
  } = useCanvasImageDrop(stageRef);

  useCanvasPlaceImage(queueDrop, viewportCenter);

  const handleDropConfirm = useCallback(
    (mode: DropResizeMode) => {
      if (!pendingDrop) return;
      const { base64, x, y, naturalW, naturalH } = pendingDrop;
      let w = naturalW;
      let h = naturalH;
      if (mode === "fit-canvas") {
        const fit = fitDimensions(naturalW, naturalH, canvas.documentWidth, canvas.documentHeight);
        w = fit.w;
        h = fit.h;
      }
      canvas.placeImageOnNewLayer(base64, Math.max(0, x - w / 2), Math.max(0, y - h / 2), w, h);
    },
    [pendingDrop, canvas],
  );

  const handleNewDocument = useCallback(() => setShowNewDocModal(true), []);

  const handleNewDocumentConfirm = useCallback(
    (w: number, h: number, bg: string) => {
      canvas.resetDocument();
      canvas.setDocumentSize(w, h);
      canvas.setDocumentBgColor(bg);
    },
    [canvas],
  );

  const handleApplySettings = useCallback(
    (w: number, h: number, bg: string) => {
      canvas.setDocumentSize(w, h);
      canvas.setDocumentBgColor(bg);
    },
    [canvas],
  );

  useEffect(() => {
    try { localStorage.setItem("canvas_grid_locked", String(gridLocked)); } catch { /* */ }
  }, [gridLocked]);
  useEffect(() => {
    try { localStorage.setItem("canvas_fit_to_view", String(isFitToView)); } catch { /* */ }
  }, [isFitToView]);
  useEffect(() => {
    try { localStorage.setItem("canvas_center_view", String(isCenterView)); } catch { /* */ }
  }, [isCenterView]);
  useEffect(() => {
    try { localStorage.setItem("canvas_asset_tab", assetTab ?? "none"); } catch { /* */ }
  }, [assetTab]);
  useEffect(() => {
    try { localStorage.setItem(LS_LEFT_W, String(leftPanelW)); } catch { /* */ }
  }, [leftPanelW]);

  if (!isLoaded) {
    return (
      <div className="canvas-panel d-flex align-items-center justify-content-center h-100">
        <div className="spinner-border spinner-border-sm text-theme-secondary" role="status" />
      </div>
    );
  }

  const toolSettingsLabel = showImagePrompt
    ? "Image Prompt"
    : (TOOL_LABELS[canvas.activeTool] ?? canvas.activeTool);

  const showBrushControls = !showImagePrompt &&
    (canvas.activeTool === "brush" || canvas.activeTool === "eraser");
  const showMoveControls  = !showImagePrompt && canvas.activeTool === "move";
  const showLassoControls = !showImagePrompt && canvas.activeTool === "lasso";
  const showWandControls  = !showImagePrompt && canvas.activeTool === "wand";
  const showCropControls  = !showImagePrompt && canvas.activeTool === "crop";
  const showBucketControls = !showImagePrompt && canvas.activeTool === "bucket";
  const showSmudgeControls = !showImagePrompt && canvas.activeTool === "smudge";
  const showPipetteControls = !showImagePrompt && canvas.activeTool === "pipette";
  const showZoomControls = !showImagePrompt && canvas.activeTool === "zoom";
  const showTextControls = !showImagePrompt && canvas.activeTool === "text";
  const showGridControls = !showImagePrompt && canvas.activeTool === "grid";

  return (
    <div
      className="canvas-panel d-flex h-100 overflow-hidden flex-column"
      style={{ background: "#0a0a0f" }}
    >
      <div className="flex-grow-1 d-flex flex-column overflow-hidden min-w-0 min-h-0">
        <div className="flex-grow-1 d-flex flex-row overflow-hidden min-h-0">

          {/* ── Left panel ─────────────────────────────────────────────── */}
          <div
            style={{
              display: "flex", flexDirection: "row",
              flexShrink: 0, width: leftPanelW,
              background: "#14141e",
              borderRight: "1px solid rgba(255,255,255,0.07)",
              overflow: "hidden",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>

              <CanvasToolPanel
                activeTool={canvas.activeTool}
                onToolChange={(tool) => {
                  canvas.setActiveTool(tool);
                  setShowImagePrompt(false);
                }}
                onNewDocument={handleNewDocument}
                onOpenSettings={() => setShowSettings(true)}
                activeAssetTab={assetTab}
                onToggleLayers={() => setAssetTab((t) => t === "layers" ? null : "layers")}
                onToggleImages={() => setAssetTab((t) => t === "images" ? null : "images")}
                showImagePrompt={showImagePrompt}
                onToggleImagePrompt={() => setShowImagePrompt((v) => !v)}
              />

              {/* Tool settings section */}
              <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
                <div style={{
                  padding: "4px 8px",
                  fontSize: 10, fontWeight: 600,
                  letterSpacing: "0.08em", textTransform: "uppercase",
                  color: "rgba(255,255,255,0.4)",
                  borderBottom: "1px solid rgba(255,255,255,0.07)",
                  flexShrink: 0,
                }}>
                  {toolSettingsLabel}
                </div>
                <div style={{ flex: 1, overflow: "hidden auto", display: "flex", flexDirection: "column" }}>
                  {showImagePrompt && <ArtPromptPanel visible={true} />}
                  {showBrushControls && <BrushControls />}
                  {showMoveControls && <MoveControls />}
                  {showLassoControls && <LassoControls />}
                  {showWandControls && <WandControls />}
                  {showCropControls && <CropControls />}
                  {showBucketControls && <BucketControls />}
                  {showSmudgeControls && <SmudgeControls />}
                  {showPipetteControls && <PipetteControls />}
                  {showZoomControls && <ZoomControls />}
                  {showTextControls && <TextControls />}
                  {showGridControls && <GridControls />}
                </div>
              </div>

              {/* Bottom row: reset presets */}
              <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "3px 6px",
                borderTop: "1px solid rgba(255,255,255,0.07)",
                background: "#161620",
                flexShrink: 0,
              }}>
                <button title="Reset tool presets" style={resetBtnStyle}>
                  <RefreshCcw size={13} strokeWidth={1.75} />
                </button>
                <button title="Reset all tool presets" style={resetBtnStyle}>
                  <RefreshCcwDot size={13} strokeWidth={1.75} />
                </button>
              </div>

            </div>

            {/* Resize handle on right edge of left panel */}
            <div
              className="resize-handle"
              onMouseDown={(e) => {
                e.preventDefault();
                leftPanelDrag = { startX: e.clientX, startW: leftPanelW, setW: setLeftPanelW };
                document.body.style.cursor = "col-resize";
                document.body.style.userSelect = "none";
              }}
            />
          </div>

          {/* ── Canvas viewport ─────────────────────────────────────────── */}
          <div
            className="flex-grow-1 overflow-hidden position-relative d-flex flex-column"
            style={{ background: "#0a0a0f" }}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <div className="flex-grow-1 min-h-0 overflow-hidden">
              <CanvasStage
                ref={canvasHandleRef}
                documentWidth={canvas.documentWidth}
                documentHeight={canvas.documentHeight}
                documentBgColor={canvas.documentBgColor}
                layers={canvas.layers}
                layerGroups={canvas.layerGroups}
                displayOrder={canvas.displayOrder}
                activeLayerId={canvas.activeLayerId}
                activeGridArea={canvas.activeGridArea}
                activeTool={canvas.activeTool}
                moveMode={canvas.moveMode}
                selectedLayerIds={canvas.selectedLayerIds}
                brushSize={canvas.brushSize}
                brushColor={canvas.brushColor}
                maskStrokes={canvas.maskStrokes}
                showGrid={canvas.gridShowGrid}
                gridSize={canvas.gridSize}
                gridColor={canvas.gridColor}
                snapToGrid={canvas.snapToGrid}
                onAddStroke={canvas.addStroke}
                onMoveImage={canvas.moveImage}
                onMoveLayer={canvas.moveLayer}
                onAddMaskStroke={canvas.addMaskStroke}
                onAddLayerMaskStroke={canvas.addLayerMaskStroke}
                setActiveGridArea={canvas.setActiveGridArea}
                onUndo={canvas.undo}
                onRedo={canvas.redo}
                setActiveTool={canvas.setActiveTool}
                setActiveLayer={canvas.setActiveLayer}
                onZoomChange={setZoom}
                isFitToView={isFitToView}
                isCenterView={isCenterView}
                onFitToViewChange={setIsFitToView}
                onCenterViewChange={setIsCenterView}
                gridLayerRef={gridLayerRef}
                maskLayerRef={maskLayerRef}
                stageRef={stageRef}
                ghostLayerRef={ghostStrokes.ghostLayerRef}
                sendLiveStroke={canvasSync.sendLiveStroke}
                sendStrokeEnd={canvasSync.sendStrokeEnd}
              />
            </div>
            <CanvasStatusBar
              documentWidth={canvas.documentWidth}
              documentHeight={canvas.documentHeight}
              zoom={zoom}
              gridWidth={canvas.activeGridArea.width}
              gridHeight={canvas.activeGridArea.height}
              activeLayer={canvas.activeLayer}
              isFitToView={isFitToView}
              isCenterView={isCenterView}
              onZoomOut={() => canvasHandleRef.current?.zoomOut()}
              onZoomReset={() => canvasHandleRef.current?.zoomReset()}
              onZoomIn={() => canvasHandleRef.current?.zoomIn()}
              onCenterView={() => canvasHandleRef.current?.centerView()}
              onFitView={() => canvasHandleRef.current?.fitView()}
            />
          </div>

          <CanvasAssetsSidebar visible={assetTab !== null} activeTab={assetTab ?? "layers"} />
        </div>
      </div>

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
