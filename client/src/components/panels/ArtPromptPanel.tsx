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
import { useArtPromptState } from "./art-prompt/useArtPromptState";

// side-effect: injects CSS for sliders / number spinners
import "./art-prompt/ArtShared";

export default function ArtPromptPanel({ visible = true }: { visible?: boolean }) {
  const s = useArtPromptState();

  if (!visible) return null;

  return (
    <Fragment>
      <div className="flex-grow-1 d-flex flex-column overflow-hidden w-100">

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

              {s.openPopup === "promptSettings" && s.promptSettingsAnchor && createPortal(
                <div
                  id="art-prompt-settings-popup"
                  className="bg-theme-panel"
                  style={{
                    position: "fixed",
                    left: s.promptSettingsAnchor.left,
                    bottom: s.promptSettingsAnchor.bottom,
                    border: "1px solid rgba(255,255,255,0.14)",
                    borderRadius: 6,
                    zIndex: 1300,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                    minWidth: 180,
                    overflow: "hidden",
                  }}
                  onMouseDown={(e) => e.stopPropagation()}
                >
                  {/* New Prompt */}
                  <button
                    type="button"
                    onClick={() => { s.handleClearPrompts(); s.togglePopup("promptSettings"); }}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      width: "100%", padding: "8px 12px",
                      border: "none", background: "transparent",
                      color: "var(--theme-text)", cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                  >
                    <LucideIcon name="message-square-plus" size={14} />
                    <span>New Prompt</span>
                  </button>

                  {/* Save Prompt */}
                  <button
                    type="button"
                    onClick={() => { s.handleSavePrompt(); s.togglePopup("promptSettings"); }}
                    disabled={s.saving || !s.prompt.trim()}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      width: "100%", padding: "8px 12px",
                      border: "none", background: "transparent",
                      color: "var(--theme-text)", cursor: s.saving || !s.prompt.trim() ? "default" : "pointer",
                      fontSize: "0.8rem", opacity: s.saving || !s.prompt.trim() ? 0.4 : 1,
                    }}
                    onMouseEnter={(e) => {
                      if (!(s.saving || !s.prompt.trim()))
                        (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)";
                    }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                  >
                    <LucideIcon name={s.saving ? "loader" : "save"} size={14} />
                    <span>Save Prompt</span>
                  </button>

                  {/* Load saved prompts */}
                  <button
                    type="button"
                    onClick={() => { s.togglePanel("savedPrompts"); s.togglePopup("promptSettings"); }}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      width: "100%", padding: "8px 12px",
                      border: "none", background: "transparent",
                      color: "var(--theme-text)", cursor: "pointer",
                      fontSize: "0.8rem",
                      borderTop: "1px solid rgba(255,255,255,0.08)",
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                  >
                    <LucideIcon name="folder-open" size={14} />
                    <span>Load saved prompts</span>
                  </button>
                </div>,
                document.body
              )}

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
              <PromptControls ref={s.controlsRef}
                generating={s.generating}
                progress={s.progress}
                phase={s.phase}
                hasPrompt={!!s.prompt.trim()}
                saving={s.saving}
                promptPopupOpen={s.openPopup === "promptSettings"}
                promptBtnRef={s.promptBtnRef}
                activeLoras={s.activeLoras}
                activeEmbeddings={s.activeEmbeddings}
                isMultiPrompt={s.isMultiPrompt}
                loraPanelOpen={s.openPanel === "lora"}
                embeddingsPanelOpen={s.openPanel === "embeddings"}
                onClear={s.handleClearPrompts}
                onSave={s.handleSavePrompt}
                onToggleSavedPrompts={() => s.togglePanel("savedPrompts")}
                onTogglePromptPopup={() => s.togglePopup("promptSettings")}
                onToggleLora={() => s.togglePanel("lora")}
                onToggleEmbeddings={() => s.togglePanel("embeddings")}
                onGenerate={s.onGenerate}
                onCancel={s.onCancel}
              />
            </div>
          </div>
        </div>
      </div>

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
