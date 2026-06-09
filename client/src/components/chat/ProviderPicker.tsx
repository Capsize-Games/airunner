import { useState, useRef, useEffect } from "react";
import Form from "react-bootstrap/Form";
import LucideIcon from "../shared/LucideIcon";

const PROVIDERS = [
  { value: "local", label: "Local" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "ollama", label: "Ollama" },
  { value: "openai", label: "OpenAI" },
];

interface Props {
  value: string;
  apiKey: string;
  apiBaseUrl: string;
  statusDotColor: string;
  statusDotTitle: string;
  onChangeProvider: (v: string) => void;
  onChangeApiKey: (v: string) => void;
  onChangeApiBaseUrl: (v: string) => void;
}

export function ProviderPicker({
  value,
  apiKey,
  apiBaseUrl,
  statusDotColor,
  statusDotTitle,
  onChangeProvider,
  onChangeApiKey,
  onChangeApiBaseUrl,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const openPicker = () => {
    setOpen((v) => {
      if (!v) window.dispatchEvent(new Event("chat-picker-opened"));
      return !v;
    });
  };

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const label = PROVIDERS.find((p) => p.value === value)?.label ?? value;
  const isOllama = value === "ollama";
  const needsApiKey = value === "openrouter" || value === "openai";

  return (
    <div ref={ref} style={{ position: "relative", flexShrink: 0 }}>
      <button
        type="button"
        onClick={openPicker}
        title={statusDotTitle}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 5,
          background: "transparent",
          border: "none",
          cursor: "pointer",
          padding: "2px 6px",
          borderRadius: 4,
          color: "var(--theme-text)",
          fontSize: "0.75rem",
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
            width: 7,
            height: 7,
            borderRadius: "50%",
            backgroundColor: statusDotColor,
            flexShrink: 0,
            display: "inline-block",
          }}
        />
        {label}
        <LucideIcon name="chevrons-up-down" size={11} />
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 4px)",
            left: 0,
            background: "var(--theme-panel-bg)",
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 6,
            padding: "4px 0",
            zIndex: 1200,
            minWidth: 160,
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
          }}
        >
          {PROVIDERS.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => {
                onChangeProvider(p.value);
                const stillNeedsInput =
                  p.value === "ollama" ||
                  p.value === "openrouter" ||
                  p.value === "openai";
                if (!stillNeedsInput) setOpen(false);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                width: "100%",
                padding: "5px 12px",
                background:
                  p.value === value ? "rgba(13,110,253,0.10)" : "transparent",
                border: "none",
                borderLeft: p.value === value
                  ? "2px solid var(--bs-primary)"
                  : "2px solid transparent",
                cursor: "pointer",
                textAlign: "left",
                color:
                  p.value === value
                    ? "var(--bs-primary)"
                    : "var(--theme-text)",
                fontSize: "0.8rem",
              }}
              onMouseEnter={(e) => {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.background = p.value === value
                  ? "rgba(13,110,253,0.18)"
                  : "rgba(255,255,255,0.08)";
              }}
              onMouseLeave={(e) => {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.background = p.value === value
                  ? "rgba(13,110,253,0.10)"
                  : "transparent";
              }}
            >
              {p.label}
            </button>
          ))}

          {(isOllama || needsApiKey) && (
            <div
              style={{
                padding: "6px 10px 6px",
                borderTop: "1px solid rgba(255,255,255,0.08)",
                marginTop: 4,
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              {isOllama && (
                <Form.Control
                  size="sm"
                  value={apiBaseUrl}
                  onChange={(e) => onChangeApiBaseUrl(e.target.value)}
                  placeholder="Ollama URL (default: http://localhost:11434)"
                  style={{ fontSize: "0.72rem" }}
                  autoFocus
                />
              )}
              {needsApiKey && (
                <Form.Control
                  size="sm"
                  type="password"
                  value={apiKey}
                  onChange={(e) => onChangeApiKey(e.target.value)}
                  placeholder={`${label} API key`}
                  style={{ fontSize: "0.72rem" }}
                  autoFocus
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
