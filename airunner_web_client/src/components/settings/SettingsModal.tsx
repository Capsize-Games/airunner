import { useState } from "react";
import Button from "react-bootstrap/Button";
import PrivacySecuritySection from "./sections/PrivacySecurity";
import ImageExportSection from "./sections/ImageExportSection";
import MemorySection from "./sections/MemorySection";
import KeyboardShortcutsSection from "./sections/KeyboardShortcutsSection";
import AgentSection from "./sections/AgentSection";
import UserSection from "./sections/UserSection";
import TTSSection from "./sections/TTSSection";
import PromptTemplatesSection from "./sections/PromptTemplatesSection";
import AppearanceSection from "./sections/AppearanceSection";
import SoundSection from "./sections/SoundSection";
import LanguageSection from "./sections/LanguageSection";

type SectionId =
  | "privacy"
  | "image-export"
  | "memory"
  | "keyboard-shortcuts"
  | "agent"
  | "user"
  | "tts"
  | "prompt-templates"
  | "appearance"
  | "sound"
  | "language";

interface NavEntry {
  id: SectionId;
  label: string;
  icon: string;
  group?: string;
  indent?: boolean;
}

const NAV_ENTRIES: NavEntry[] = [
  { id: "privacy",           label: "Third-party Services",  icon: "\uD83D\uDD12" },
  { id: "image-export",      label: "Image Export",          icon: "\uD83D\uDDBC" },
  { id: "memory",            label: "Memory",                icon: "\uD83E\uDDE0" },
  { id: "keyboard-shortcuts",label: "Keyboard Shortcuts",    icon: "\u2328" },
  { id: "agent",             label: "Agent Preferences",     icon: "\uD83E\uDD16" },
  { id: "user",              label: "User Settings",         icon: "\uD83D\uDC64" },
  { id: "tts",               label: "Text-to-Speech",        icon: "\uD83D\uDCE2" },
  { id: "sound",             label: "Speech-to-Text",        icon: "\uD83C\uDF99" },
  { id: "prompt-templates",  label: "Prompt Templates",      icon: "\uD83D\uDCDD" },
  { id: "appearance",        label: "Theme",                 icon: "\uD83C\uDFA8" },
  { id: "language",          label: "Language",              icon: "\uD83C\uDF0D" },
];

function getGroupEntries(
  entries: NavEntry[],
): { group: string; items: NavEntry[] }[] {
  const topLevel = entries.filter((e) => !e.group);
  const result: { group: string; items: NavEntry[] }[] = [
    { group: "", items: topLevel },
  ];
  return result;
}

const LS_KEY = "airunner_settings_section";

export default function SettingsModal({
  onClose,
}: {
  onClose: () => void;
}) {
  const [activeSection, setActiveSection] = useState<SectionId>(() => {
    try {
      const saved = localStorage.getItem(LS_KEY);
      if (saved && NAV_ENTRIES.some((e) => e.id === saved)) {
        return saved as SectionId;
      }
    } catch { /* ignore */ }
    return "privacy";
  });

  function handleNavClick(id: SectionId) {
    setActiveSection(id);
    try { localStorage.setItem(LS_KEY, id); } catch { /* ignore */ }
  }

  function renderSection() {
    switch (activeSection) {
      case "privacy":
        return <PrivacySecuritySection />;
      case "image-export":
        return <ImageExportSection />;
      case "memory":
        return <MemorySection />;
      case "keyboard-shortcuts":
        return <KeyboardShortcutsSection />;
      case "agent":
        return <AgentSection />;
      case "user":
        return <UserSection />;
      case "tts":
        return <TTSSection />;
      case "prompt-templates":
        return <PromptTemplatesSection />;
      case "appearance":
        return <AppearanceSection />;
      case "sound":
        return <SoundSection />;
      case "language":
        return <LanguageSection />;
      default:
        return <PrivacySecuritySection />;
    }
  }

  const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

  return (
    <div className="settings-modal-backdrop" onClick={onClose}>
      <div
        className="settings-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Settings"
      >
        <div className="settings-modal-header">
          <h5 className="mb-0">Settings</h5>
          <Button
            variant="link"
            className="text-light p-0 d-flex align-items-center"
            onClick={onClose}
            size="sm"
          >
            <img
              src={icon("circle-x")}
              alt="Close"
              style={{ width: 20, height: 20, filter: "invert(0.6)" }}
            />
          </Button>
        </div>
        <div className="settings-modal-body">
          <nav className="settings-nav">
            {NAV_ENTRIES.map((entry) => (
              <button
                key={entry.id}
                className={
                  "settings-nav-item" +
                  (activeSection === entry.id ? " active" : "")
                }
                onClick={() => handleNavClick(entry.id)}
              >
                <span>{entry.icon}</span>
                <span>{entry.label}</span>
              </button>
            ))}
          </nav>
          <div className="settings-content">{renderSection()}</div>
        </div>
      </div>
    </div>
  );
}
