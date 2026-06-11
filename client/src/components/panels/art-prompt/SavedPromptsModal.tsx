import { useState, useEffect, useCallback } from "react";
import {
  listSavedPrompts,
  deleteSavedPrompt,
  type SavedPrompt,
} from "../../../api/art";
import LucideIcon from "../../shared/LucideIcon";

interface Props {
  version: string;
  onLoad: (p: SavedPrompt) => void;
  onClose: () => void;
}

export default function SavedPromptsPanel({
  version,
  onLoad,
  onClose,
}: Props) {
  const [prompts, setPrompts] = useState<SavedPrompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<number | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSavedPrompts(version || undefined);
      setPrompts(data.prompts ?? []);
    } catch {
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, [version]);

  useEffect(() => { reload(); }, [reload]);

  const handleDelete = async (id: number) => {
    setDeleting(id);
    try {
      await deleteSavedPrompt(id);
      setPrompts((prev) => prev.filter((p) => p.id !== id));
    } catch {
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="d-flex flex-column h-100">
      {/* Sticky header */}
      <div
        className="sticky-top flex-shrink-0 d-flex align-items-center bg-theme-panel border-b-theme"
        style={{ padding: "8px 12px 6px", zIndex: 1 }}
      >
        <span className="text-panel-label text-uppercase">
          Saved Prompts
        </span>
      </div>

      {/* Scrollable body */}
      <div className="overflow-y-auto flex-grow-1">
        {loading ? (
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 40, color: "var(--theme-text-secondary)", gap: 8, fontSize: 13,
          }}>
            <LucideIcon name="loader" size={16} />
            Loading…
          </div>
        ) : prompts.length === 0 ? (
          <div className="d-flex flex-column align-items-center justify-content-center text-theme-secondary" style={{ padding: 40, gap: 8 }}>
            <span style={{ fontSize: 12 }}>No saved prompts yet.</span>
          </div>
        ) : (
          prompts.map((p) => (
            <div
              key={p.id}
              style={{
                display: "flex", alignItems: "flex-start", gap: 8,
                padding: "8px 12px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <div className="flex-grow-1 min-w-0">
                <div style={{
                  fontSize: 12, color: "var(--theme-text)", fontWeight: 500,
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {p.prompt || <em style={{ opacity: 0.4 }}>empty prompt</em>}
                </div>
                {p.negative_prompt && (
                  <div style={{
                    fontSize: 11, color: "var(--theme-text-secondary)", opacity: 0.7,
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    marginTop: 2,
                  }}>
                    {p.negative_prompt}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                <button
                  type="button"
                  onClick={() => { onLoad(p); onClose(); }}
                  title="Load this prompt"
                  style={{
                    display: "flex", alignItems: "center", gap: 4,
                    padding: "3px 8px",
                    background: "rgba(var(--theme-primary-rgb), 0.12)",
                    border: "1px solid rgba(var(--theme-primary-rgb), 0.25)",
                    borderRadius: 4, color: "var(--bs-primary)",
                    cursor: "pointer", fontSize: 11, fontWeight: 600,
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLButtonElement).style.background = "rgba(var(--theme-primary-rgb), 0.22)")
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLButtonElement).style.background = "rgba(var(--theme-primary-rgb), 0.12)")
                  }
                >
                  Load
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(p.id)}
                  disabled={deleting === p.id}
                  title="Delete"
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    width: 26, height: 26, padding: 0,
                    background: "transparent", border: "1px solid transparent",
                    borderRadius: 4, color: "var(--theme-text-secondary)",
                    cursor: "pointer", opacity: deleting === p.id ? 0.4 : 1,
                  }}
                  onMouseEnter={(e) => {
                    const btn = e.currentTarget as HTMLButtonElement;
                    btn.style.color = "var(--bs-danger)";
                    btn.style.borderColor = "rgba(var(--bs-danger-rgb), 0.3)";
                    btn.style.background = "rgba(var(--bs-danger-rgb), 0.10)";
                  }}
                  onMouseLeave={(e) => {
                    const btn = e.currentTarget as HTMLButtonElement;
                    btn.style.color = "var(--theme-text-secondary)";
                    btn.style.borderColor = "transparent";
                    btn.style.background = "transparent";
                  }}
                >
                  <LucideIcon name="trash" size={13} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
