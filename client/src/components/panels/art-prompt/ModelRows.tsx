import type { ArtOptionsResponse } from "../../../api/client";
import { ArtDropdownPicker } from "./ArtDropdownPicker";
import { Divider } from "./ArtShared";

interface Props {
  version: string;
  modelPath: string;
  scheduler: string;
  schedulerOptions: { label: string; value: string }[];
  loading: boolean;
  artOptions: ArtOptionsResponse | null;
  onVersionChange: (v: string) => void;
  onModelChange: (m: string) => void;
  onSchedulerChange: (s: string) => void;
}

const ROW_STYLE: React.CSSProperties = {
  display: "flex", alignItems: "center",
  padding: "2px 4px",
  borderTop: "1px solid rgba(255,255,255,0.08)",
  flexShrink: 0,
  minWidth: 0,
};

export function ModelRows({ version, modelPath, scheduler, schedulerOptions, loading, artOptions, onVersionChange, onModelChange, onSchedulerChange }: Props) {
  const versionInfo = artOptions?.versions?.find((v) => v.name === version);
  const availableModels = versionInfo?.models ?? [];

  if (loading) {
    return (
      <div style={{ ...ROW_STYLE, justifyContent: "center", padding: "4px" }}>
        <div className="spinner-border spinner-border-sm" role="status"
          style={{ color: "var(--theme-text-secondary)", width: 11, height: 11 }} />
      </div>
    );
  }

  return (
    <div style={ROW_STYLE}>
      <ArtDropdownPicker
        value={version}
        placeholder="Version…"
        options={artOptions?.versions?.map((v) => ({ label: v.name, value: v.name })) ?? []}
        onChange={onVersionChange}
      />
      <Divider />
      <ArtDropdownPicker
        value={modelPath}
        placeholder={version ? "Model…" : "Version…"}
        options={availableModels}
        onChange={onModelChange}
        disabled={!version || availableModels.length === 0}
      />
      <Divider />
      <ArtDropdownPicker
        value={scheduler}
        placeholder="Scheduler…"
        options={schedulerOptions}
        onChange={onSchedulerChange}
        disabled={!version || schedulerOptions.length === 0}
      />
    </div>
  );
}
