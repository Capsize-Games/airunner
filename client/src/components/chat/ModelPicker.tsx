import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import Form from "react-bootstrap/Form";
import LucideIcon from "../shared/LucideIcon";

interface Props {
  value: string;
  isLocal: boolean;
  isOllama: boolean;
  localModels: { label: string; value: string }[];
  onChangeModel: (v: string) => void;
}

export function ModelPicker({
  value,
  isLocal,
  isOllama,
  localModels,
  onChangeModel,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [anchor, setAnchor] = useState<{ left: number; bottom: number } | null>(null);

  const openPicker = () => {
    setOpen((v) => {
      const next = !v;
      if (next) {
        window.dispatchEvent(new Event("chat-picker-opened"));
        if (btnRef.current) {
          const r = btnRef.current.getBoundingClientRect();
          setAnchor({ left: r.left, bottom: window.innerHeight - r.top + 4 });
        }
      }
      return next;
    });
  };

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  useEffect(() => {
    const handler = () => setOpen(false);
    window.addEventListener("art-overlay-opened", handler);
    return () => window.removeEventListener("art-overlay-opened", handler);
  }, []);

  const stripPathAndExt = (s: string) =>
    (s.split("/").pop() ?? s).replace(/\.(gguf|bin|safetensors|pt|pth|ckpt|pkl|model)$/i, "");

  const displayLabel = isLocal
    ? stripPathAndExt(
        localModels.find((m) => m.value === value)?.label ??
        (value || "Select model…")
      )
    : value || (isOllama ? "Model name…" : "Model ID…");

  const filtered = localModels.filter(
    (m) => !query || m.label.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div ref={containerRef} className="min-w-0" style={{ flex: "1 1 0%" }}>
      <button
        ref={btnRef}
        type="button"
        onClick={openPicker}
        title={value || "Select model"}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          maxWidth: "100%",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: "2px 6px",
          borderRadius: 4,
          color: value ? "var(--theme-text)" : "rgba(255,255,255,0.35)",
          fontSize: "0.75rem",
          overflow: "hidden",
          width: "100%",
        }}
        onMouseEnter={(e) =>
          ((e.currentTarget as HTMLButtonElement).style.background =
            "rgba(255,255,255,0.08)")
        }
        onMouseLeave={(e) =>
          ((e.currentTarget as HTMLButtonElement).style.background =
            "transparent")
        }
      >
        <span
          style={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {displayLabel}
        </span>
        <LucideIcon name="chevrons-up-down" size={11} />
      </button>

      {open && anchor && createPortal(
        <div
          className="d-flex flex-column bg-theme-panel"
          style={{
            position: "fixed",
            left: anchor.left,
            bottom: anchor.bottom,
            minWidth: 220,
            maxWidth: 340,
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 6,
            zIndex: 1300,
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            maxHeight: 300,
          }}
        >
          {isLocal ? (
            <>
              <div className="flex-shrink-0 border-b-subtle" style={{ padding: "6px 8px" }}>
                <Form.Control
                  size="sm"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search models…"
                  style={{ fontSize: "0.75rem" }}
                  autoFocus
                />
              </div>
              <div className="overflow-y-auto flex-grow-1">
                {filtered.length === 0 && (
                  <div
                    style={{
                      padding: "8px 12px",
                      fontSize: "0.75rem",
                      color: "rgba(255,255,255,0.35)",
                    }}
                  >
                    No models found
                  </div>
                )}
                {filtered.map((m) => (
                  <button
                    key={m.value}
                    type="button"
                    onClick={() => {
                      onChangeModel(m.value);
                      setOpen(false);
                      setQuery("");
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      width: "100%",
                      padding: "5px 12px",
                      background:
                        m.value === value
                          ? "rgba(13,110,253,0.10)"
                          : "transparent",
                      border: "none",
                      borderLeft:
                        m.value === value
                          ? "2px solid var(--bs-primary)"
                          : "2px solid transparent",
                      cursor: "pointer",
                      textAlign: "left",
                      color:
                        m.value === value
                          ? "var(--bs-primary)"
                          : "var(--theme-text)",
                      fontSize: "0.78rem",
                    }}
                    onMouseEnter={(e) => {
                      const btn = e.currentTarget as HTMLButtonElement;
                      btn.style.background =
                        m.value === value
                          ? "rgba(13,110,253,0.18)"
                          : "rgba(255,255,255,0.08)";
                    }}
                    onMouseLeave={(e) => {
                      const btn = e.currentTarget as HTMLButtonElement;
                      btn.style.background =
                        m.value === value
                          ? "rgba(13,110,253,0.10)"
                          : "transparent";
                    }}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div style={{ padding: 8 }}>
              <Form.Control
                size="sm"
                value={value}
                onChange={(e) => onChangeModel(e.target.value)}
                placeholder={isOllama ? "Model name (e.g. llama3)" : "Model ID"}
                style={{ fontSize: "0.75rem" }}
                autoFocus
              />
            </div>
          )}
        </div>,
        document.body,
      )}
    </div>
  );
}
