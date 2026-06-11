import { useState } from "react";
import LucideIcon from "../../shared/LucideIcon";
import InfoItem from "./InfoItem";

interface SeedInfoRowProps {
  seed: number;
  seedRandomized: boolean;
  focusedField: string | null;
  onToggleFocused: (field: string) => void;
  onSeedChange: (v: number) => void;
  onToggleRandom: () => void;
}

export default function SeedInfoRow({
  seed,
  seedRandomized,
  focusedField,
  onToggleFocused,
  onSeedChange,
  onToggleRandom,
}: SeedInfoRowProps) {
  const [seedCopied, setSeedCopied] = useState(false);
  const editing = focusedField === "seed";

  return (
    <InfoItem
      icon="shuffle"
      label={seedRandomized ? "Seed (random)" : "Seed (fixed)"}
      dimmed={seedRandomized}
      editing={editing}
      onClick={() => onToggleFocused("seed")}
      editor={
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <input
            type="number" className="art-no-spin" value={seed}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (!isNaN(v)) onSeedChange(v);
            }}
            style={{
              height: 22, width: 80,
              background: "var(--theme-input-bg)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 4, color: "var(--theme-text)",
              fontSize: 10, textAlign: "center", padding: "0 4px",
            }}
          />
        </div>
      }
    >
      <div style={{ display: "flex", alignItems: "center", gap: 4, flex: 1, minWidth: 0 }}>
        {!editing && (
          <span style={{ color: "var(--theme-text)", opacity: seedRandomized ? 0.35 : 1, fontSize: 10 }}>
            {String(seed)}
          </span>
        )}
        {!editing && (
          <button type="button"
            title={seedRandomized ? "Seed: switch to fixed" : "Seed: switch to random"}
            onClick={(e) => { e.stopPropagation(); onToggleRandom(); }}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: 18, height: 18, padding: 0, border: "none",
              cursor: "pointer", borderRadius: 3,
              background: seedRandomized ? "rgba(var(--bs-primary-rgb), 0.15)" : "transparent",
              color: seedRandomized ? "var(--bs-primary)" : "rgba(255,255,255,0.35)",
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              if (!seedRandomized) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)";
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
              }
            }}
            onMouseLeave={(e) => {
              if (!seedRandomized) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.35)";
                (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              }
            }}
          >
            <LucideIcon name="shuffle" size={10} />
          </button>
        )}
        {!editing && (
          <button type="button"
            title={seedCopied ? "Copied!" : "Copy seed to clipboard"}
            onClick={(e) => {
              e.stopPropagation();
              navigator.clipboard.writeText(String(seed));
              setSeedCopied(true);
              setTimeout(() => setSeedCopied(false), 1500);
            }}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: 18, height: 18, padding: 0, border: "none",
              background: "transparent", cursor: "pointer", borderRadius: 3,
              color: seedCopied ? "var(--bs-primary)" : "rgba(255,255,255,0.35)",
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              if (!seedCopied) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)";
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
              }
            }}
            onMouseLeave={(e) => {
              if (!seedCopied) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.35)";
                (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              }
            }}
          >
            <LucideIcon name={seedCopied ? "check" : "copy"} size={10} />
          </button>
        )}
      </div>
    </InfoItem>
  );
}
