import { useState, useRef, useEffect } from "react";
import LucideIcon from "../../shared/LucideIcon";

interface Props {
  value: string;
  placeholder: string;
  options: { label: string; value: string }[];
  onChange: (v: string) => void;
  disabled?: boolean;
}

export function ArtDropdownPicker({
  value,
  placeholder,
  options,
  onChange,
  disabled,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const rawLabel = options.find((o) => o.value === value)?.label ?? (value || placeholder);
  const label = rawLabel === placeholder
    ? rawLabel
    : (rawLabel.split("/").pop() ?? rawLabel).replace(/\.(gguf|bin|safetensors|pt|pth|ckpt|pkl|model|safetensor)$/i, "");

  return (
    <div ref={ref} style={{ position: "relative", flex: "1 1 0%", minWidth: 0 }}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        title={label}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          width: "100%",
          background: "transparent",
          border: "none",
          cursor: disabled ? "default" : "pointer",
          padding: "2px 6px",
          borderRadius: 4,
          color: value ? "var(--theme-text)" : "var(--theme-text-secondary)",
          fontSize: "0.75rem",
          overflow: "hidden",
          opacity: disabled ? 0.4 : 1,
        }}
        onMouseEnter={(e) => {
          if (!disabled)
            (e.currentTarget as HTMLButtonElement).style.background =
              "rgba(var(--theme-text-rgb), 0.08)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "transparent";
        }}
      >
        <span
          style={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            flex: 1,
            textAlign: "left",
          }}
        >
          {label}
        </span>
        <LucideIcon name="chevrons-up-down" size={11} />
      </button>

      {open && !disabled && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 4px)",
            left: 0,
            minWidth: 160,
            maxWidth: 280,
            background: "var(--theme-panel-bg)",
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 6,
            zIndex: 1200,
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            maxHeight: 240,
            overflowY: "auto",
          }}
        >
          {options.length === 0 ? (
            <div
              style={{
                padding: "8px 12px",
                fontSize: "0.75rem",
                color: "var(--theme-text-secondary)",
              }}
            >
              No options
            </div>
          ) : (
            options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  width: "100%",
                  padding: "5px 12px",
                  background:
                    opt.value === value
                      ? "rgba(var(--theme-primary-rgb), 0.10)"
                      : "transparent",
                  border: "none",
                  borderLeft:
                    opt.value === value
                      ? "2px solid var(--bs-primary)"
                      : "2px solid transparent",
                  cursor: "pointer",
                  textAlign: "left",
                  color:
                    opt.value === value ? "var(--bs-primary)" : "var(--theme-text)",
                  fontSize: "0.78rem",
                }}
                onMouseEnter={(e) => {
                  const btn = e.currentTarget as HTMLButtonElement;
                  btn.style.background =
                    opt.value === value
                      ? "rgba(var(--theme-primary-rgb), 0.18)"
                      : "rgba(var(--theme-text-rgb), 0.08)";
                }}
                onMouseLeave={(e) => {
                  const btn = e.currentTarget as HTMLButtonElement;
                  btn.style.background =
                    opt.value === value
                      ? "rgba(var(--theme-primary-rgb), 0.10)"
                      : "transparent";
                }}
              >
                {opt.label}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
