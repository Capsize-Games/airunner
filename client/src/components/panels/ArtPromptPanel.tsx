import { Fragment, useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { Alert } from "react-bootstrap";
import { PromptTextareas } from "./art-prompt/PromptTextareas";
import { PromptControls } from "./art-prompt/PromptControls";
import { useArtPromptState } from "./art-prompt/useArtPromptState";
import { useArtOverlays } from "./art-prompt/useArtOverlays";
import GenerationInfoPanel from "./art-prompt/GenerationInfoPanel";
import InfoDropdownPopup from "./art-prompt/InfoDropdownPopup";
import ArtPanelPopup from "./art-prompt/ArtPanelPopup";
import { saveToStorage } from "./art-model/ArtModelStorage";
import LucideIcon from "../shared/LucideIcon";
import SourceImagePanel from "./art-prompt/SourceImagePanel";
import SizePopup from "./art-prompt/SizePopup";

// side-effect: injects CSS for sliders / number spinners
import "./art-prompt/ArtShared";

export default function ArtPromptPanel({
  visible = true,
  generationType: externalGenerationType,
  onGenerationTypeChange: externalOnGenerationTypeChange,
}: {
  visible?: boolean;
  generationType?: "txt2img" | "img2img" | "inpaint";
  onGenerationTypeChange?: (v: "txt2img" | "img2img" | "inpaint") => void;
}) {
  const s = useArtPromptState({ generationType: externalGenerationType });
  const o = useArtOverlays();

  // Use external generationType props when provided (e.g. from CanvasPanel),
  // otherwise fall back to the internal state from useArtPromptState.
  const genType = externalGenerationType ?? s.generationType;
  const onGenTypeChange = externalOnGenerationTypeChange ?? s.setGenerationType;

  const [showInfo, setShowInfo] = useState(() => {
    try {
      return (
        localStorage.getItem("airunner_show_gen_info") !== "false"
      );
    } catch {
      return true;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem("airunner_show_gen_info", String(showInfo));
    } catch {}
  }, [showInfo]);

  if (!visible) return null;

  return (
    <Fragment>
      <div className="flex-grow-1 d-flex flex-column overflow-hidden w-100">
        <div className="d-flex flex-column flex-grow-1 overflow-hidden">
          <div
            className="flex-grow-1 d-flex flex-column bg-theme-panel overflow-hidden min-h-0"
            style={{ border: "none", borderRadius: 0 }}
          >

            <PromptTextareas
              prompt={s.prompt}
              secondaryPrompt={s.secondaryPrompt}
              negativePrompt={s.negativePrompt}
              secondaryNegativePrompt={s.secondaryNegativePrompt}
              isMultiPrompt={s.isMultiPrompt}
              generating={s.generating}
              onPromptChange={(v) => {
                s.setPrompt(v);
                s.persist({ prompt: v });
              }}
              onSecondaryPromptChange={(v) => {
                s.setSecondaryPrompt(v);
                s.persist({ secondary_prompt: v });
              }}
              onNegativePromptChange={(v) => {
                s.setNegativePrompt(v);
                s.persist({ negative_prompt: v });
              }}
              onSecondaryNegativePromptChange={(v) => {
                s.setSecondaryNegativePrompt(v);
                s.persist({ secondary_negative_prompt: v });
              }}
            />

            {/* ── Source image panel (img2img / inpaint) ─────────────
             * Shown only when generation type is img2img or inpaint. */}
            {(genType === "img2img" || genType === "inpaint") && (
              <SourceImagePanel
                generationType={genType}
                strength={s.strength}
                onStrengthChange={s.setStrength}
                feather={s.feather}
                onFeatherChange={s.setFeather}
              />
            )}

            <GenerationInfoPanel
              showInfo={showInfo}
              onToggleShowInfo={() => setShowInfo((v) => !v)}
              version={s.version}
              modelPath={s.modelPath}
              scheduler={s.scheduler}
              steps={s.steps}
              cfgScale={s.cfgScale}
              nSamples={s.nSamples}
              imagesPerBatch={s.imagesPerBatch}
              generationType={genType}
              seed={s.seed}
              seedRandomized={s.seedRandomized}
              genWidth={s.genWidth}
              genHeight={s.genHeight}
              activeLoras={s.activeLoras}
              activeEmbeddings={s.activeEmbeddings}
              isMultiPrompt={s.isMultiPrompt}
              artOptions={s.artOptions}
              onVersionChange={s.handleVersion}
              onModelChange={s.handleModel}
              onSchedulerChange={s.handleScheduler}
              onStepsChange={s.setSteps}
              onCfgScaleChange={s.setCfgScale}
              onNSamplesChange={s.setNSamples}
              onImagesPerBatchChange={s.setImagesPerBatch}
              onGenerationTypeChange={onGenTypeChange}
              onSeedChange={s.handleSeedChange}
              onToggleRandom={s.handleToggleRandom}
              onGenWidthChange={s.setGenWidth}
              onGenHeightChange={s.setGenHeight}
              onToggleLoraPanel={(anchorRect) => s.togglePanel("lora", anchorRect)}
              onToggleEmbeddingsPanel={(anchorRect) =>
                s.togglePanel("embeddings", anchorRect)
              }
              persistGen={s.persistGen}
              openDropdown={o.openDropdown}
              toggleGenSize={o.toggleGenSize}
            />


            {s.errorMessage && (
              <div
                style={{
                  padding: "0 6px 4px",
                  flexShrink: 0,
                }}
              >
                <Alert
                  variant="danger"
                  dismissible
                  style={{
                    margin: 0,
                    padding: "4px 8px",
                    fontSize: "0.75rem",
                    lineHeight: 1.3,
                  }}
                  onClose={() => s.setErrorMessage(null)}
                >
                  {s.errorMessage}
                </Alert>
              </div>
            )}

            <div
              ref={s.toolbarRef}
              className="flex-shrink-0 d-flex flex-column"
            >
              <PromptControls
                ref={s.controlsRef}
                generating={s.generating}
                progress={s.progress}
                phase={s.phase}
                hasPrompt={!!s.prompt.trim()}
                saving={s.saving}
                promptPopupOpen={
                  s.openPopup === "promptSettings"
                }
                promptBtnRef={s.promptBtnRef}
                activeLoras={s.activeLoras}
                activeEmbeddings={s.activeEmbeddings}
                isMultiPrompt={s.isMultiPrompt}
                loraPanelOpen={s.openPanel === "lora"}
                embeddingsPanelOpen={
                  s.openPanel === "embeddings"
                }
                seedRandomized={s.seedRandomized}
                onClear={s.handleClearPrompts}
                onSave={s.handleSavePrompt}
                onToggleSavedPrompts={() =>
                  s.togglePanel("savedPrompts")
                }
                onTogglePromptPopup={() =>
                  s.togglePopup("promptSettings")
                }
                onToggleLora={() => s.togglePanel("lora")}
                onToggleEmbeddings={() =>
                  s.togglePanel("embeddings")
                }
                onToggleRandom={s.handleToggleRandom}
                onGenerate={s.onGenerate}
                onCancel={s.onCancel}
              />
            </div>
          </div>
        </div>
      </div>

      <InfoDropdownPopup
        field={o.dropdownField}
        anchor={o.dropdownAnchor}
        version={s.version}
        modelPath={s.modelPath}
        scheduler={s.scheduler}
        generationType={genType}
        artOptions={s.artOptions}
        availableSchedulers={s.availableSchedulers}
        onSelectVersion={s.handleVersion}
        onSelectModel={s.handleModel}
        onSelectScheduler={s.handleScheduler}
        onSelectGenType={onGenTypeChange}
        onClose={o.closeDropdown}
      />

      <ArtPanelPopup
        openPanel={s.openPanel}
        anchor={s.artPanelAnchor}
        version={s.version}
        onLoadPrompt={s.handleLoadPrompt}
        onCloseSavedPrompts={() =>
          s.togglePanel("savedPrompts")
        }
      />

      {/* ── Prompt settings popup ────────────────────────────────────
       * Rendered via portal above the prompt-settings button in
       * PromptControls. Shows New Prompt / Save Prompt / Load saved
       * prompts actions. */}
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
        document.body,
      )}
      {o.showGenSize && (
        <SizePopup
          anchor={o.genSizeAnchor}
          portalId={o.genSizePortalId}
          genWidth={s.genWidth}
          genHeight={s.genHeight}
          onWidthChange={(v) => { s.setGenWidth(v); saveToStorage("gen_width", v); s.persistGen({ width: v }); }}
          onHeightChange={(v) => { s.setGenHeight(v); saveToStorage("gen_height", v); s.persistGen({ height: v }); }}
          persistGen={s.persistGen}
        />
      )}
    </Fragment>
  );
}
