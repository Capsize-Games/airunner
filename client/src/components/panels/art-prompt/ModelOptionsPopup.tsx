import { createPortal } from "react-dom";
import LucideIcon from "../../shared/LucideIcon";
import { ArtDropdownPicker } from "./ArtDropdownPicker";
import type { ArtOptionsResponse } from "../../../api/client";

interface ModelOptionsPopupProps {
  anchor: { left: number; bottom: number } | null;
  version: string;
  modelPath: string;
  scheduler: string;
  artOptions: ArtOptionsResponse | null;
  availableSchedulers: { label: string; value: string }[];
  onVersionChange: (v: string) => void;
  onModelChange: (m: string) => void;
  onSchedulerChange: (s: string) => void;
}

export default function ModelOptionsPopup({
  anchor,
  version,
  modelPath,
  scheduler,
  artOptions,
  availableSchedulers,
  onVersionChange,
  onModelChange,
  onSchedulerChange,
}: ModelOptionsPopupProps) {
  if (!anchor) return null;

  return createPortal(
    <div
      id="art-model-options-popup"
      className="bg-theme-panel d-flex flex-column"
      style={{
        position: "fixed",
        left: anchor.left,
        bottom: anchor.bottom,
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 6,
        zIndex: 1300,
        boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
        minWidth: 220,
        padding: "8px 0",
        gap: 4,
      }}
    >
      <div
        style={{
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          color: "var(--theme-text-secondary)",
          opacity: 0.6,
          padding: "4px 10px 2px",
        }}
      >
        Art Model Options
      </div>

      {/* Version */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          padding: "4px 10px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.07em",
            textTransform: "uppercase",
            color: "var(--theme-text-secondary)",
            opacity: 0.6,
          }}
        >
          <LucideIcon name="circle-dot" size={9} />
          <span>Version</span>
        </div>
        <ArtDropdownPicker
          value={version}
          placeholder="Choose version…"
          options={
            artOptions?.versions?.map((v) => ({
              label: v.name,
              value: v.name,
            })) ?? []
          }
          onChange={onVersionChange}
        />
      </div>

      {/* Model */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          padding: "4px 10px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.07em",
            textTransform: "uppercase",
            color: "var(--theme-text-secondary)",
            opacity: 0.6,
          }}
        >
          <LucideIcon name="circle-dot" size={9} />
          <span>Model</span>
        </div>
        <ArtDropdownPicker
          value={modelPath}
          placeholder="Choose model…"
          options={
            artOptions?.versions?.find((v) => v.name === version)?.models ?? []
          }
          onChange={onModelChange}
          disabled={!version}
        />
      </div>

      {/* Scheduler */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          padding: "4px 10px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.07em",
            textTransform: "uppercase",
            color: "var(--theme-text-secondary)",
            opacity: 0.6,
          }}
        >
          <LucideIcon name="circle-dot" size={9} />
          <span>Scheduler</span>
        </div>
        <ArtDropdownPicker
          value={scheduler}
          placeholder="Choose scheduler…"
          options={availableSchedulers}
          onChange={onSchedulerChange}
          disabled={!version || availableSchedulers.length === 0}
        />
      </div>
    </div>,
    document.body,
  );
}
