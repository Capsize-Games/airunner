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
import LoraPanel from "./LoraPanel";
import EmbeddingsPanel from "./EmbeddingsPanel";
import { SettingsPopup } from "./art-prompt/SettingsPopup";
import { ArtDropdownPicker } from "./art-prompt/ArtDropdownPicker";
import { saveToStorage } from "./art-model/ArtModelStorage";
import LucideIcon from "../shared/LucideIcon";

// side-effect: injects CSS for sliders / number spinners
import "./art-prompt/ArtShared";

export default function ArtPromptPanel({
  visible = true,
  activeArtAction = null,
  generationType: externalGenerationType,
  onGenerationTypeChange: externalOnGenerationTypeChange,
}: {
  visible?: boolean;
  activeArtAction?: string | null;
  generationType?: "txt2img" | "img2img" | "inpaint";
  onGenerationTypeChange?: (v: "txt2img" | "img2img" | "inpaint") => void;
}) {
  const s = useArtPromptState();
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
            {/* ── Tool options section ──────────────────────────────────
             * Always present. Shows inline settings when a palette
             * button is active; empty otherwise. */}
            <div className="flex-shrink-0" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
              {activeArtAction && (
                <div className="overflow-y-auto" style={{ padding: "6px 8px", maxHeight: 260 }}>
                  {activeArtAction === "modelOptions" && (
                    <div className="d-flex flex-column" style={{ gap: 6, padding: "2px 4px" }}>
                      <div className="d-flex flex-column" style={{ gap: 8 }}>
                        <div className="d-flex flex-column" style={{ gap: 2 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 9, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--theme-text-secondary)", opacity: 0.6 }}>
                            <LucideIcon name="circle-dot" size={9} /> Version
                          </div>
                          <ArtDropdownPicker value={s.version} placeholder="Choose version…"
                            options={s.artOptions?.versions?.map((v: { name: string }) => ({ label: v.name, value: v.name })) ?? []}
                            onChange={s.handleVersion}
                          />
                        </div>
                        <div className="d-flex flex-column" style={{ gap: 2 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 9, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--theme-text-secondary)", opacity: 0.6 }}>
                            <LucideIcon name="circle-dot" size={9} /> Model
                          </div>
                          <ArtDropdownPicker value={s.modelPath} placeholder="Choose model…"
                            options={s.artOptions?.versions?.find((v: { name: string }) => v.name === s.version)?.models ?? []}
                            onChange={s.handleModel} disabled={!s.version}
                          />
                        </div>
                        <div className="d-flex flex-column" style={{ gap: 2 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 9, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--theme-text-secondary)", opacity: 0.6 }}>
                            <LucideIcon name="circle-dot" size={9} /> Scheduler
                          </div>
                          <ArtDropdownPicker value={s.scheduler} placeholder="Choose scheduler…"
                            options={s.availableSchedulers}
                            onChange={s.handleScheduler} disabled={!s.version || s.availableSchedulers.length === 0}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                  {activeArtAction === "embeddings" && <EmbeddingsPanel hideHeader />}
                  {activeArtAction === "lora" && <LoraPanel hideHeader />}
                  {activeArtAction === "settings" && (
                    <div>
                      <SettingsPopup
                        hideHeader
                        steps={s.steps} cfgScale={s.cfgScale} nSamples={s.nSamples} imagesPerBatch={s.imagesPerBatch}
                        onStepsChange={(v) => { s.setSteps(v); s.persistGen({ steps: v }); }}
                        onCfgScaleChange={(v) => { s.setCfgScale(v); s.persistGen({ cfg_scale: v }); }}
                        onNSamplesChange={(v) => { s.setNSamples(v); s.persistGen({ n_samples: v }); }}
                        onImagesPerBatchChange={(v) => { s.setImagesPerBatch(v); s.persistGen({ images_per_batch: v }); }}
                      />
                    </div>
                  )}
                  {activeArtAction === "seed" && (
                    <div style={{ padding: "6px 4px" }}>
                      <div className="d-flex align-items-center" style={{ gap: 6 }}>
                        <button
                          type="button"
                          title={s.seedRandomized ? "Switch to fixed seed" : "Switch to random seed"}
                          onClick={s.handleToggleRandom}
                          style={{
                            display: "flex", alignItems: "center", justifyContent: "center",
                            width: 28, height: 24, padding: 0,
                            background: s.seedRandomized ? "rgba(99,153,255,0.22)" : "transparent",
                            border: "none", borderRadius: 4, cursor: "pointer",
                            color: s.seedRandomized ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
                          }}
                        >
                          <LucideIcon name="shuffle" size={12} />
                        </button>
                        <input
                          type="number"
                          className="art-no-spin"
                          value={s.seedRandomized ? "" : s.seed}
                          placeholder={s.seedRandomized ? "Random" : String(s.seed)}
                          disabled={s.seedRandomized}
                          onChange={(e) => s.handleSeedChange(Number(e.target.value))}
                          style={{
                            flex: 1, height: 24,
                            background: "var(--theme-input-bg)",
                            border: "1px solid rgba(255,255,255,0.12)",
                            borderRadius: 4, color: "var(--theme-text)",
                            fontSize: 11, padding: "0 6px",
                            opacity: s.seedRandomized ? 0.5 : 1,
                          }}
                        />
                      </div>
                    </div>
                  )}
                  {activeArtAction === "imageSize" && (
                    <div style={{ padding: "6px 4px" }}>
                      <div className="d-flex flex-column" style={{ gap: 6 }}>
                        <div className="d-flex align-items-center" style={{ gap: 6 }}>
                          <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>W</span>
                          <input type="number" className="art-no-spin" value={s.genWidth}
                            onChange={(e) => s.setGenWidth(Number(e.target.value))}
                            onBlur={(e) => { const v = Math.max(64, Math.min(2048, Number(e.target.value))); s.setGenWidth(v); saveToStorage("gen_width", v); s.persistGen({ width: v }); }}
                            style={{ height: 22, background: "var(--theme-input-bg)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "var(--theme-text)", fontSize: 10, textAlign: "center", padding: "0 2px", width: 72 }}
                          />
                        </div>
                        <div className="d-flex align-items-center" style={{ gap: 6 }}>
                          <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>H</span>
                          <input type="number" className="art-no-spin" value={s.genHeight}
                            onChange={(e) => s.setGenHeight(Number(e.target.value))}
                            onBlur={(e) => { const v = Math.max(64, Math.min(2048, Number(e.target.value))); s.setGenHeight(v); saveToStorage("gen_height", v); s.persistGen({ height: v }); }}
                            style={{ height: 22, background: "var(--theme-input-bg)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "var(--theme-text)", fontSize: 10, textAlign: "center", padding: "0 2px", width: 72 }}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

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
              onToggleLoraPanel={() => s.togglePanel("lora")}
              onToggleEmbeddingsPanel={() =>
                s.togglePanel("embeddings")
              }
              persistGen={s.persistGen}
              openDropdown={o.openDropdown}
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
        openPanel={s.openPanel === "savedPrompts" ? "savedPrompts" : null}
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
    </Fragment>
  );
}
