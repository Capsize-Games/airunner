import { useRef, useState, useCallback, useEffect } from "react";
import Konva from "konva";
import { useCanvasContext, useCanvasDocument } from "../../features/canvas";
import type { CanvasStageHandle } from "../../features/canvas/CanvasStage";
import CanvasStage from "../../features/canvas/CanvasStage";
import ToolBar, { type ToolbarDock } from "../../features/canvas/ToolBar";
import CanvasSettingsModal from "../../features/canvas/CanvasSettingsModal";
import ImageDropModal, { fitDimensions, type DropResizeMode } from "../../features/canvas/ImageDropModal";
import CanvasLayersSidebar from "../../features/canvas/CanvasLayersSidebar";

interface PendingDrop {
  base64: string;
  x: number;
  y: number;
  naturalW: number;
  naturalH: number;
}

export default function CanvasPanel() {
  const canvas = useCanvasContext();

  const stageRef        = useRef<Konva.Stage>(null!) as React.RefObject<Konva.Stage>;
  const gridLayerRef    = useRef<Konva.Layer>(null!) as React.RefObject<Konva.Layer>;
  const maskLayerRef    = useRef<Konva.Layer>(null!) as React.RefObject<Konva.Layer>;
  const canvasHandleRef = useRef<CanvasStageHandle>(null);

  const [showGrid,       setShowGrid]       = useState(true);
  const [zoom,           setZoom]           = useState(1);
  const [gridLocked,     setGridLocked]     = useState(false);
  const [showSettings,   setShowSettings]   = useState(false);
  const [showLayers,     setShowLayers]     = useState(true);
  const [pendingDrop,    setPendingDrop]    = useState<PendingDrop | null>(null);
  const [showDropModal,  setShowDropModal]  = useState(false);

  const [dock, setDock] = useState<ToolbarDock>(() =>
    (localStorage.getItem("canvas_toolbar_dock") as ToolbarDock | null) ?? "top",
  );

  const handleSetDock = useCallback((d: ToolbarDock) => {
    setDock(d);
    localStorage.setItem("canvas_toolbar_dock", d);
  }, []);

  const documentString = JSON.stringify(canvas.getSerializedState());
  const { isLoaded } = useCanvasDocument({
    documentString,
    onLoad: canvas.loadFromJSON,
    isDirty: true,
  });

  // ── Image drop helpers ────────────────────────────────────────────────────

  const canvasDropPos = useCallback((clientX: number, clientY: number) => {
    const stage = stageRef.current;
    if (!stage) return { x: 0, y: 0 };
    const rect = stage.container().getBoundingClientRect();
    const scale = stage.scaleX();
    return {
      x: (clientX - rect.left - stage.x()) / scale,
      y: (clientY - rect.top  - stage.y()) / scale,
    };
  }, [stageRef]);

  const queueDrop = useCallback((dataUrl: string, x: number, y: number) => {
    const img = new Image();
    img.onload = () => {
      setPendingDrop({ base64: dataUrl, x, y, naturalW: img.naturalWidth, naturalH: img.naturalHeight });
      setShowDropModal(true);
    };
    img.src = dataUrl;
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    // Capture canvas coords synchronously before any async work
    const { x, y } = canvasDropPos(e.clientX, e.clientY);

    // Case 1: file dragged from filesystem
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const dataUrl = ev.target?.result as string;
        if (dataUrl) queueDrop(dataUrl, x, y);
      };
      reader.readAsDataURL(file);
      return;
    }

    // Case 2: URL dragged from image browser panel
    const imageUrl = e.dataTransfer.getData("text/image-url");
    if (imageUrl) {
      fetch(imageUrl)
        .then((r) => r.blob())
        .then((blob) => {
          const reader = new FileReader();
          reader.onload = (ev) => {
            const dataUrl = ev.target?.result as string;
            if (dataUrl) queueDrop(dataUrl, x, y);
          };
          reader.readAsDataURL(blob);
        })
        .catch(() => { /* silently ignore */ });
    }
  }, [canvasDropPos, queueDrop]);

  // Listen for the "canvas-place-image" event fired by ServerImageRow's button
  useEffect(() => {
    const handler = (e: Event) => {
      const { imageUrl } = (e as CustomEvent<{ imageUrl: string }>).detail;
      if (!imageUrl) return;
      fetch(imageUrl)
        .then((r) => r.blob())
        .then((blob) => {
          const reader = new FileReader();
          reader.onload = (ev) => {
            const dataUrl = ev.target?.result as string;
            if (dataUrl) queueDrop(dataUrl, 0, 0);
          };
          reader.readAsDataURL(blob);
        })
        .catch(() => { /* silently ignore */ });
    };
    window.addEventListener("canvas-place-image", handler);
    return () => window.removeEventListener("canvas-place-image", handler);
  }, [queueDrop]);

  const handleDropConfirm = useCallback((mode: DropResizeMode) => {
    if (!pendingDrop) return;
    const { base64, x, y, naturalW, naturalH } = pendingDrop;
    let w = naturalW;
    let h = naturalH;
    if (mode === "fit-grid") {
      const fit = fitDimensions(naturalW, naturalH, canvas.activeGridArea.width, canvas.activeGridArea.height);
      w = fit.w; h = fit.h;
    } else if (mode === "fit-canvas") {
      const fit = fitDimensions(naturalW, naturalH, canvas.documentWidth, canvas.documentHeight);
      w = fit.w; h = fit.h;
    }
    canvas.placeImageOnNewLayer(base64, Math.max(0, x - w / 2), Math.max(0, y - h / 2), w, h);
    setPendingDrop(null);
  }, [pendingDrop, canvas]);

  // ── Canvas settings ───────────────────────────────────────────────────────

  const handleApplySettings = useCallback((w: number, h: number, bg: string) => {
    canvas.setDocumentSize(w, h);
    canvas.setDocumentBgColor(bg);
  }, [canvas]);

  if (!isLoaded) {
    return (
      <div className="canvas-panel d-flex align-items-center justify-content-center h-100">
        <div className="spinner-border spinner-border-sm" role="status" style={{ color: "var(--theme-text-secondary)" }} />
      </div>
    );
  }

  const isVertical = dock === "left" || dock === "right";

  return (
    <div
      className={`canvas-panel d-flex h-100 overflow-hidden ${isVertical ? "flex-row" : "flex-column"}`}
      style={{ background: "#0a0a0f" }}
    >
      {(dock === "top" || dock === "left") && (
        <ToolBar
          activeTool={canvas.activeTool}
          brushSize={canvas.brushSize}
          brushColor={canvas.brushColor}
          showGrid={showGrid}
          snapToGrid={canvas.snapToGrid}
          zoom={zoom}
          activeGridArea={canvas.activeGridArea}
          gridLocked={gridLocked}
          dock={dock}
          onSetActiveTool={canvas.setActiveTool}
          onSetBrushSize={canvas.setBrushSize}
          onSetBrushColor={canvas.setBrushColor}
          onToggleGrid={() => setShowGrid((v) => !v)}
          onToggleSnap={() => canvas.setSnapToGrid(!canvas.snapToGrid)}
          onZoomIn={() => canvasHandleRef.current?.zoomIn()}
          onZoomOut={() => canvasHandleRef.current?.zoomOut()}
          onZoomReset={() => canvasHandleRef.current?.zoomReset()}
          onCenterView={() => canvasHandleRef.current?.centerView()}
          onSetGridArea={canvas.setActiveGridArea}
          onToggleGridLock={() => setGridLocked((v) => !v)}
          onOpenSettings={() => setShowSettings(true)}
          onSetDock={handleSetDock}
          onUndo={canvas.undo}
          onRedo={canvas.redo}
          onNewDocument={canvas.resetDocument}
          onClearMask={canvas.clearMask}
          hasMaskStrokes={canvas.maskStrokes.length > 0}
          showLayers={showLayers}
          onToggleLayers={() => setShowLayers((v) => !v)}
        />
      )}

      {/* Canvas viewport + layers sidebar */}
      <div
        className="flex-grow-1 d-flex flex-column overflow-hidden"
        style={{ minWidth: 0, minHeight: 0 }}
      >
        {/* Canvas + optional layers sidebar, side by side */}
        <div className="flex-grow-1 d-flex flex-row overflow-hidden" style={{ minHeight: 0 }}>
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
        </div>

        {/* Status bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "3px 10px",
            background: "#111118",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            fontSize: 11,
            fontFamily: "monospace",
            color: "rgba(255,255,255,0.4)",
            flexShrink: 0,
          }}
        >
          <span>{canvas.documentWidth} × {canvas.documentHeight}</span>
          <span>Zoom: {Math.round(zoom * 100)}%</span>
          <span>Grid: {canvas.activeGridArea.width} × {canvas.activeGridArea.height}</span>
          {canvas.activeLayer && <span>Layer: {canvas.activeLayer.name}</span>}
        </div>
      </div>

      {(dock === "bottom" || dock === "right") && (
        <ToolBar
          activeTool={canvas.activeTool}
          brushSize={canvas.brushSize}
          brushColor={canvas.brushColor}
          showGrid={showGrid}
          snapToGrid={canvas.snapToGrid}
          zoom={zoom}
          activeGridArea={canvas.activeGridArea}
          gridLocked={gridLocked}
          dock={dock}
          onSetActiveTool={canvas.setActiveTool}
          onSetBrushSize={canvas.setBrushSize}
          onSetBrushColor={canvas.setBrushColor}
          onToggleGrid={() => setShowGrid((v) => !v)}
          onToggleSnap={() => canvas.setSnapToGrid(!canvas.snapToGrid)}
          onZoomIn={() => canvasHandleRef.current?.zoomIn()}
          onZoomOut={() => canvasHandleRef.current?.zoomOut()}
          onZoomReset={() => canvasHandleRef.current?.zoomReset()}
          onCenterView={() => canvasHandleRef.current?.centerView()}
          onSetGridArea={canvas.setActiveGridArea}
          onToggleGridLock={() => setGridLocked((v) => !v)}
          onOpenSettings={() => setShowSettings(true)}
          onSetDock={handleSetDock}
          onUndo={canvas.undo}
          onRedo={canvas.redo}
          onNewDocument={canvas.resetDocument}
          onClearMask={canvas.clearMask}
          hasMaskStrokes={canvas.maskStrokes.length > 0}
          showLayers={showLayers}
          onToggleLayers={() => setShowLayers((v) => !v)}
        />
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
