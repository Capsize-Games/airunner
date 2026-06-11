import { Fragment, useState, useEffect } from "react";
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
}: {
  visible?: boolean;
  activeArtAction?: string | null;
}) {
  const s = useArtPromptState();
  const o = useArtOverlays();

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
            className="flex-grow-1 d-flex flex-column bg-theme-input overflow-hidden min-h-0"
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
                  {activeArtAction === "genType" && (
                    <div className="d-flex flex-column" style={{ gap: 2, padding: "4px 2px" }}>
                      <button type="button" onClick={() => s.setGenerationType("txt2img")}
                        style={{ display: "flex", flexDirection: "column", gap: 1, width: "100%", padding: "4px 10px", border: "none", background: s.generationType === "txt2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent", cursor: "pointer", textAlign: "left", color: s.generationType === "txt2img" ? "var(--bs-primary)" : "var(--theme-text)", fontSize: "0.75rem", borderLeft: s.generationType === "txt2img" ? "2px solid var(--bs-primary)" : "2px solid transparent", borderRadius: 2 }}
                      >Text-to-image</button>
                      <button type="button" onClick={() => s.setGenerationType("img2img")}
                        style={{ display: "flex", flexDirection: "column", gap: 1, width: "100%", padding: "4px 10px", border: "none", background: s.generationType === "img2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent", cursor: "pointer", textAlign: "left", color: s.generationType === "img2img" ? "var(--bs-primary)" : "var(--theme-text)", fontSize: "0.75rem", borderLeft: s.generationType === "img2img" ? "2px solid var(--bs-primary)" : "2px solid transparent", borderRadius: 2 }}
                      >Image-to-image</button>
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
              generationType={s.generationType}
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
              onGenerationTypeChange={s.setGenerationType}
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
        generationType={s.generationType}
        artOptions={s.artOptions}
        availableSchedulers={s.availableSchedulers}
        onSelectVersion={s.handleVersion}
        onSelectModel={s.handleModel}
        onSelectScheduler={s.handleScheduler}
        onSelectGenType={s.setGenerationType}
        onClose={o.closeDropdown}
      />

      <ArtPanelPopup
        openPanel={s.openPanel === "savedPrompts" ? "savedPrompts" : null}
        anchor={s.artPanelAnchor}
        onLoadPrompt={s.handleLoadPrompt}
        onCloseSavedPrompts={() =>
          s.togglePanel("savedPrompts")
        }
      />
    </Fragment>
  );
}
