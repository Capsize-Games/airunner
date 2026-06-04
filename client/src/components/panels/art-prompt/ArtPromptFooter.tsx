import ProgressBar from "react-bootstrap/ProgressBar";
import ArtModelSelector from "../../shared/ArtModelSelector";
import LucideIcon from "../../shared/LucideIcon";

export default function ArtPromptFooter({
  progress,
  generating,
  hasPrompt,
  artVersion,
  artModel,
  onVersionChange,
  onModelChange,
  onSubmit,
  onCancel,
}: {
  progress: number;
  generating: boolean;
  hasPrompt: boolean;
  artVersion: string;
  artModel: string;
  onVersionChange: (v: string) => void;
  onModelChange: (m: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="flex-shrink-0 mt-2">
      <div className="mb-1">
        <ArtModelSelector
          version={artVersion}
          modelPath={artModel}
          onVersionChange={onVersionChange}
          onModelChange={onModelChange}
        />
      </div>
      <div className="d-flex align-items-center gap-2">
        <div className="flex-grow-1">
          <ProgressBar
            now={progress}
            variant={generating ? "info" : "secondary"}
            style={{ height: 8 }}
            animated={generating && progress < 100}
          />
        </div>
        {generating ? (
          <button
            className="btn btn-sm btn-danger p-1"
            onClick={onCancel}
            title="Cancel image generation"
            style={{
              minWidth: 30, height: 30,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <LucideIcon name="circle-stop" size={16} />
          </button>
        ) : (
          <button
            className="btn btn-sm p-1 d-flex align-items-center justify-content-center"
            style={{
              background: "var(--bs-primary)",
              minWidth: 30,
              height: 30,
              border: "none",
            }}
            onClick={onSubmit}
            disabled={!hasPrompt}
            title="Generate image"
          >
            <LucideIcon name="chevron-up" size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
