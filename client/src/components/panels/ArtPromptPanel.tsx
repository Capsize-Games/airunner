import { Fragment, useState, useEffect } from "react";
import { PromptTextareas } from "./art-prompt/PromptTextareas";
import { PromptControls } from "./art-prompt/PromptControls";
import { useArtPromptState } from "./art-prompt/useArtPromptState";
import { useArtOverlays } from "./art-prompt/useArtOverlays";
import GenerationInfoPanel from "./art-prompt/GenerationInfoPanel";
import ToolbarRow from "./art-prompt/ToolbarRow";
import InfoDropdownPopup from "./art-prompt/InfoDropdownPopup";
import ArtPanelPopup from "./art-prompt/ArtPanelPopup";

// side-effect: injects CSS for sliders / number spinners
import "./art-prompt/ArtShared";

export default function ArtPromptPanel({
  visible = true,
}: {
  visible?: boolean;
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

            {!showInfo && (
              <ToolbarRow
                version={s.version}
                modelPath={s.modelPath}
                scheduler={s.scheduler}
                artOptions={s.artOptions}
                availableSchedulers={s.availableSchedulers}
                activeLoras={s.activeLoras}
                activeEmbeddings={s.activeEmbeddings}
                isMultiPrompt={s.isMultiPrompt}
                seedRandomized={s.seedRandomized}
                saving={s.saving}
                steps={s.steps}
                cfgScale={s.cfgScale}
                nSamples={s.nSamples}
                imagesPerBatch={s.imagesPerBatch}
                genWidth={s.genWidth}
                genHeight={s.genHeight}
                generationType={s.generationType}
                openPopup={s.openPopup}
                openPanel={s.openPanel}
                settingsAnchor={s.settingsAnchor}
                promptSettingsAnchor={s.promptSettingsAnchor}
                settingsBtnRef={s.settingsBtnRef}
                prompt={s.prompt}
                onVersionChange={s.handleVersion}
                onModelChange={s.handleModel}
                onSchedulerChange={s.handleScheduler}
                onToggleRandom={s.handleToggleRandom}
                onTogglePanel={(panel: string) =>
                  s.togglePanel(panel as "lora" | "embeddings" | "savedPrompts")
                }
                onTogglePopup={(popup: string) =>
                  s.togglePopup(popup as "settings" | "promptSettings")
                }
                onClearPrompts={s.handleClearPrompts}
                onSavePrompt={s.handleSavePrompt}
                onSetGenerationType={s.setGenerationType}
                onWidthChange={s.setGenWidth}
                onHeightChange={s.setGenHeight}
                onStepsChange={s.setSteps}
                onCfgScaleChange={s.setCfgScale}
                onNSamplesChange={s.setNSamples}
                onImagesPerBatchChange={s.setImagesPerBatch}
                persistGen={s.persistGen}
                showModelOptions={o.showModelOptions}
                modelOptionsBtnRef={o.modelOptionsBtnRef}
                modelOptionsAnchor={o.modelOptionsAnchor}
                showSize={o.showSize}
                sizeBtnRef={o.sizeBtnRef}
                sizeAnchor={o.sizeAnchor}
                showGenType={o.showGenType}
                genTypeBtnRef={o.genTypeBtnRef}
                genTypeAnchor={o.genTypeAnchor}
                sizePortalId={o.sizePortalId}
                toggleModelOptions={o.toggleModelOptions}
                toggleSize={o.toggleSize}
                toggleGenType={o.toggleGenType}
                closeGenType={o.closeGenType}
              />
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
        openPanel={s.openPanel}
        anchor={s.artPanelAnchor}
        onLoadPrompt={s.handleLoadPrompt}
        onCloseSavedPrompts={() =>
          s.togglePanel("savedPrompts")
        }
      />
    </Fragment>
  );
}
