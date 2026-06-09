// ── Welcome Screen ──────────────────────────────────────────────────────
import { useState } from "react";
import LucideIcon from "../shared/LucideIcon";

interface Props {
  onOpenChat: () => void;
  onOpenCanvas: () => void;
  onOpenCivitai: () => void;
}

export default function WelcomeScreen({
  onOpenChat,
  onOpenCanvas,
  onOpenCivitai,
}: Props) {
  const [hovered, setHovered] = useState<string | null>(
    null,
  );

  const items = [
    {
      key: "chat",
      icon: "bot-message-square",
      label: "Chat",
      hint: "Talk to a local LLM",
      onClick: onOpenChat,
    },
    {
      key: "canvas",
      icon: "image",
      label: "Canvas",
      hint: "Generate and edit images",
      onClick: onOpenCanvas,
    },
    {
      key: "civitai",
      icon: "globe",
      label: "CivitAI",
      hint: "Browse and download models",
      onClick: onOpenCivitai,
    },
  ];

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        color: "var(--theme-text-secondary)",
        userSelect: "none",
        padding: "40px 24px",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 12,
        }}
      >
        <img
          src="/favicon.svg"
          alt="AI Runner"
          style={{
            width: 64,
            height: 64,
            opacity: 0.25,
            filter: "grayscale(1)",
          }}
        />
        <h2
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: "var(--theme-heading)",
            margin: 0,
            opacity: 0.6,
          }}
        >
          AI Runner
        </h2>
        <p
          style={{
            margin: 0,
            fontSize: 13,
            opacity: 0.5,
            textAlign: "center",
            maxWidth: 320,
          }}
        >
          Open a panel from the sidebar to get started.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          width: "100%",
          maxWidth: 340,
        }}
      >
        {items.map(({ key, icon, label, hint, onClick }) => (
          <button
            key={key}
            type="button"
            onClick={onClick}
            onMouseEnter={() => setHovered(key)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              padding: "11px 16px",
              borderRadius: 8,
              background:
                hovered === key
                  ? "rgba(var(--theme-primary-rgb), 0.10)"
                  : "rgba(var(--theme-text-rgb), 0.03)",
              border:
                hovered === key
                  ? "1px solid rgba(var(--theme-primary-rgb), 0.30)"
                  : "1px solid rgba(var(--theme-text-rgb), 0.07)",
              cursor: "pointer",
              textAlign: "left",
              width: "100%",
              transition:
                "background 0.15s, border-color 0.15s",
            }}
          >
            <span
              style={{
                flexShrink: 0,
                color:
                  hovered === key
                    ? "var(--bs-primary)"
                    : "var(--theme-text-secondary)",
                transition: "color 0.15s",
              }}
            >
              <LucideIcon name={icon} size={20} />
            </span>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 2,
              }}
            >
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--theme-text)",
                }}
              >
                {label}
              </span>
              <span
                style={{
                  fontSize: 11,
                  color: "var(--theme-text-secondary)",
                  opacity: 0.7,
                }}
              >
                {hint}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
