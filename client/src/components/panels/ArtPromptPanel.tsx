import { Fragment } from "react";
import { createPortal } from "react-dom";
import { saveToStorage } from "./art-model/ArtModelStorage";
import SavedPromptsPanel from "./art-prompt/SavedPromptsModal";
import LucideIcon from "../shared/LucideIcon";
import { PromptTextareas } from "./art-prompt/PromptTextareas";
import { PromptToolbar } from "./art-prompt/PromptToolbar";
import { ModelRows } from "./art-prompt/ModelRows";
import { PromptControls } from "./art-prompt/PromptControls";
import { ToolbarIconBtn } from "./art-prompt/ArtShared";
import { SettingsPopup } from "./art-prompt/SettingsPopup";
import LoraPanel from "./LoraPanel";
import EmbeddingsPanel from "./EmbeddingsPanel";
import { useArtPromptState, ART_PANEL_MIN, ART_PANEL_MAX } from "./art-prompt/useArtPromptState";

// side-effect: injects CSS for sliders / number spinners
import "./art-prompt/ArtShared";

const railBtnStyle: React.CSSProperties = {
  background: "none", border: "none", cursor: "pointer",
  color: "rgba(255,255,255,0.4)", padding: 0,
  display: "flex", alignItems: "center", justifyContent: "center",
  borderRadius: 4, width: 28, height: 28, flexShrink: 0,
};

let artDragState: { startX: number; startW: number; setW: (w: number) => void } | null = null;
function onArtMouseMove(e: MouseEvent) {
  if (!artDragState) return;
  const delta = e.clientX - artDragState.startX;
  artDragState.setW(Math.max(ART_PANEL_MIN, Math.min(ART_PANEL_MAX, artDragState.startW + delta)));
}
function onArtMouseUp() {
  if (!artDragState) return;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  artDragState = null;
}
if (typeof window !== "undefined") {
  window.addEventListener("mousemove", onArtMouseMove);
  window.addEventListener("mouseup", onArtMouseUp);
}

export default function ArtPromptPanel() {
  const s = useArtPromptState();

  if (s.collapsed) {
    return (
      <div
        className="flex-shrink-0 d-flex flex-column align-items-center bg-theme-panel overflow-hidden"
        style={{ width: 32, borderRight: "1px solid var(--separator-color)", padding: "4px 0", gap: 2 }}
      >
        <button style={railBtnStyle} title="Expand art panel" onClick={() => s.collapseToStorage(false)}>
          <LucideIcon name="chevron-right" size={14} />
        </button>
        <div className="sep-h" />
        <button style={railBtnStyle} title="Prompt" onClick={() => s.collapseToStorage(false)}>
          <LucideIcon name="message-square-heart" size={14} />
        </button>
      </div>
    );
  }

  return (
    <Fragment>
      <div className="flex-shrink-0 d-flex flex-column overflow-hidden" style={{ width: s.artW }}>
        <div className="d-flex align-items-center flex-shrink-0 border-b-theme" style={{ padding: "2px 4px" }}>
          <button
            type="button" onClick={() => s.collapseToStorage(true)} title="Collapse art panel"
            style={{ ...railBtnStyle, width: 24, height: 24, color: "var(--theme-text-secondary)", flexShrink: 0 }}
          >
            <LucideIcon name="chevron-left" size={13} />
          </button>
          <span style={{ fontSize: 10, fontWeight: 700, color: "var(--theme-text-secondary)", letterSpacing: "0.06em", paddingLeft: 4 }}>
            ART PROMPT
          </span>
        </div>

        <div className="d-flex flex-column flex-grow-1 overflow-hidden">
          <div className="flex-grow-1 d-flex flex-column bg-theme-input overflow-hidden min-h-0" style={{ border: "none", borderRadius: 0 }}>
            <PromptTextareas
              prompt={s.prompt}
              secondaryPrompt={s.secondaryPrompt}
              negativePrompt={s.negativePrompt}
              secondaryNegativePrompt={s.secondaryNegativePrompt}
              isMultiPrompt={s.isMultiPrompt}
              generating={s.generating}
              onPromptChange={(v) => { s.setPrompt(v); s.persist({ prompt: v }); }}
              onSecondaryPromptChange={(v) => { s.setSecondaryPrompt(v); s.persist({ secondary_prompt: v }); }}
              onNegativePromptChange={(v) => { s.setNegativePrompt(v); s.persist({ negative_prompt: v }); }}
              onSecondaryNegativePromptChange={(v) => { s.setSecondaryNegativePrompt(v); s.persist({ secondary_negative_prompt: v }); }}
            />

            <div style={{
              display: "flex", alignItems: "center", gap: 4,
              padding: "2px 6px",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              flexShrink: 0,
            }}>
              <div ref={s.settingsBtnRef}>
                <ToolbarIconBtn
                  title="Generation settings"
                  onClick={() => s.togglePopup("settings")}
                  active={s.openPopup === "settings"}
                >
                  <LucideIcon name="settings-2" size={14} />
                </ToolbarIconBtn>
              </div>
              {s.openPopup === "settings" && s.settingsAnchor && createPortal(
                <div id="art-settings-popup" className="bg-theme-panel overflow-y-auto" style={{
                  position: "fixed",
                  left: s.settingsAnchor.left,
                  bottom: s.settingsAnchor.bottom,
                  border: "1px solid rgba(255,255,255,0.14)",
                  borderRadius: 6,
                  zIndex: 1300,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                  maxHeight: 400,
                  minWidth: 260,
                }}>
                  <SettingsPopup
                    steps={s.steps}
                    cfgScale={s.cfgScale}
                    nSamples={s.nSamples}
                    imagesPerBatch={s.imagesPerBatch}
                    onStepsChange={(v) => { s.setSteps(v); saveToStorage("steps", v); s.persistGen({ steps: v }); }}
                    onCfgScaleChange={(v) => { s.setCfgScale(v); saveToStorage("cfg_scale", v); s.persistGen({ cfg_scale: v }); }}
                    onNSamplesChange={(v) => { s.setNSamples(v); saveToStorage("n_samples", v); s.persistGen({ n_samples: v }); }}
                    onImagesPerBatchChange={(v) => { s.setImagesPerBatch(v); saveToStorage("images_per_batch", v); s.persistGen({ images_per_batch: v }); }}
                  />
                </div>,
                document.body
              )}

              <span className="flex-grow-1" />

              <ToolbarIconBtn
                title={`LoRA${s.activeLoras.length > 0 ? ` (${s.activeLoras.length})` : ""}`}
                onClick={() => s.togglePanel("lora")}
                active={s.openPanel === "lora"}
                badge={s.activeLoras.length > 0 ? s.activeLoras.length : undefined}
              >
                <LucideIcon name="puzzle" size={14} />
              </ToolbarIconBtn>
              <ToolbarIconBtn
                title={`Embeddings${s.activeEmbeddings.length > 0 ? ` (${s.activeEmbeddings.length})` : ""}`}
                onClick={() => s.togglePanel("embeddings")}
                active={s.openPanel === "embeddings"}
                badge={s.activeEmbeddings.length > 0 ? s.activeEmbeddings.length : undefined}
              >
                <LucideIcon name="scan-text" size={14} />
              </ToolbarIconBtn>
            </div>

            <ModelRows
              version={s.version}
              modelPath={s.modelPath}
              scheduler={s.scheduler}
              schedulerOptions={s.availableSchedulers}
              loading={s.toolbarLoading}
              artOptions={s.artOptions}
              onVersionChange={s.handleVersion}
              onModelChange={s.handleModel}
              onSchedulerChange={s.handleScheduler}
            />

            <div ref={s.toolbarRef} className="flex-shrink-0 d-flex flex-column">
              <PromptToolbar
                seed={s.seed}
                seedRandomized={s.seedRandomized}
                genWidth={s.genWidth}
                genHeight={s.genHeight}
                onSeedChange={s.handleSeedChange}
                onToggleRandom={s.handleToggleRandom}
                onWidthChange={(v) => { s.setGenWidth(v); saveToStorage("gen_width", v); s.persistGen({ width: v }); }}
                onHeightChange={(v) => { s.setGenHeight(v); saveToStorage("gen_height", v); s.persistGen({ height: v }); }}
              />
              <PromptControls
                generating={s.generating}
                progress={s.progress}
                phase={s.phase}
                hasPrompt={!!s.prompt.trim()}
                saving={s.saving}
                onClear={s.handleClearPrompts}
                onSave={s.handleSavePrompt}
                onToggleSavedPrompts={() => s.togglePanel("savedPrompts")}
                onGenerate={s.onGenerate}
                onCancel={s.onCancel}
              />
            </div>
          </div>
        </div>
      </div>

      <div
        className="resize-handle"
        onMouseDown={(e) => {
          e.preventDefault();
          artDragState = { startX: e.clientX, startW: s.artW, setW: s.setArtW };
          document.body.style.cursor = "col-resize";
          document.body.style.userSelect = "none";
        }}
      />

      {s.openPanel && s.artPanelAnchor && (
        <div
          id="art-panel-popup"
          className="bg-theme-panel d-flex flex-column overflow-hidden"
          style={{
            position: "fixed",
            left: s.artPanelAnchor.left,
            bottom: s.artPanelAnchor.bottom,
            width: s.artPanelAnchor.width,
            height: s.artPanelAnchor.height,
            zIndex: 1300,
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 0,
            boxShadow: "4px -4px 24px rgba(0,0,0,0.7)",
          }}
        >
          {s.openPanel === "lora" && <LoraPanel />}
          {s.openPanel === "embeddings" && <EmbeddingsPanel />}
          {s.openPanel === "savedPrompts" && (
            <SavedPromptsPanel
              onLoad={s.handleLoadPrompt}
              onClose={() => s.togglePanel("savedPrompts")}
            />
          )}
        </div>
      )}
    </Fragment>
  );
}
