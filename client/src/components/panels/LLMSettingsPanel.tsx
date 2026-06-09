import Form from "react-bootstrap/Form";
import ModelSelector from "../chat/ModelSelector";
import PresetSelector from "./llm-settings/PresetSelector";
import SliderFields from "./llm-settings/SliderFields";
import CheckboxFields from "./llm-settings/CheckboxFields";
import PrecisionSelector from "./llm-settings/PrecisionSelector";
import ConversationSection from "./llm-settings/ConversationSection";
import LucideIcon from "../shared/LucideIcon";
import { useLLMSettings } from "./llm-settings/useLLMSettings";

export function LLMSettingsPanel() {
  const s = useLLMSettings();

  if (s.loading) {
    return (
      <div className="p-2 small" style={{ color: "var(--theme-text-secondary)" }}>
        Loading...
      </div>
    );
  }

  return (
    <div className="p-2">
      <h6 style={{ color: "var(--theme-text-secondary)" }} className="mb-2">LLM Settings</h6>
      <ModelSelector />

      <div className="p-2 mt-2" style={{ border: "1px solid #333", borderRadius: 6 }}>
        <Form.Check
          type="switch"
          id="llm-override-toggle"
          label={
            <span style={{ color: "var(--theme-text-secondary)", fontWeight: 600 }}>
              Override LLM Settings
            </span>
          }
          checked={s.overrideEnabled}
          onChange={(e) => s.setOverrideEnabled(e.target.checked)}
        />

        {s.overrideEnabled && (
          <>
            <PresetSelector
              presets={s.presets}
              overriddenLabels={s.overriddenLabels}
              selectedPreset={s.selectedPreset}
              overrideEnabled={s.overrideEnabled}
              selectKey={s.selectKey}
              handlePresetChange={s.handlePresetChange}
            />

            {s.selectedPreset !== "" && (
              <>
                <SliderFields
                  presets={s.presets}
                  activePresetRef={s.activePresetRef}
                  collectValues={s.collectValues}
                  setOverride={s.setOverride}
                />
                <CheckboxFields
                  collectValues={s.collectValues}
                  setOverride={s.setOverride}
                />
                <PrecisionSelector
                  precisionOptions={s.precisionOptions}
                  precision={s.precision}
                  onChange={s.handlePrecisionChange}
                />
                <ConversationSection
                  performConversationSummary={s.performConversationSummary}
                  summarizeAfterNTurns={s.summarizeAfterNTurns}
                  onSummaryToggle={s.setPerformConversationSummary}
                  onTurnsChange={s.setSummarizeAfterNTurns}
                />
                <div className="d-flex gap-2 mt-1">
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary flex-fill"
                    onClick={s.resetToDefaults}
                    title="Reset the current preset to its default values"
                    style={{ color: "var(--theme-text-secondary)", borderColor: "#444" }}
                  >
                    <LucideIcon name="rotate-ccw-square" size={14} className="me-1" />
                    Reset {s.selectedPreset}
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary flex-fill"
                    onClick={s.resetAllToDefaults}
                    title="Reset all presets to their default values"
                    style={{ color: "var(--theme-text-secondary)", borderColor: "#444" }}
                  >
                    <LucideIcon name="rotate-ccw-square" size={14} className="me-1" />
                    Reset All
                  </button>
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
