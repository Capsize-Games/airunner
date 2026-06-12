import type { ArtPanel } from "./ArtShared";
import LoraPanel from "../LoraPanel";
import EmbeddingsPanel from "../EmbeddingsPanel";
import SavedPromptsPanel from "./SavedPromptsModal";
import type { SavedPrompt } from "../../../api/art";

interface ArtPanelPopupProps {
  openPanel: ArtPanel;
  anchor: {
    left: number;
    bottom: number;
    width: number;
    height: number;
  } | null;
  version: string;
  onLoadPrompt: (p: SavedPrompt) => void;
  onCloseSavedPrompts: () => void;
}

export default function ArtPanelPopup({
  openPanel,
  anchor,
  version,
  onLoadPrompt,
  onCloseSavedPrompts,
}: ArtPanelPopupProps) {
  if (!openPanel || !anchor) return null;

  return (
    <div
      id="art-panel-popup"
      className="bg-theme-panel d-flex flex-column overflow-hidden"
      style={{
        position: "fixed",
        left: anchor.left,
        bottom: anchor.bottom,
        width: anchor.width,
        height: anchor.height,
        zIndex: 1300,
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 0,
        boxShadow: "4px -4px 24px rgba(0,0,0,0.7)",
      }}
    >
      {openPanel === "lora" && <LoraPanel />}
      {openPanel === "embeddings" && <EmbeddingsPanel />}
      {openPanel === "savedPrompts" && (
        <SavedPromptsPanel
          version={version}
          onLoad={onLoadPrompt}
          onClose={onCloseSavedPrompts}
        />
      )}
    </div>
  );
}
