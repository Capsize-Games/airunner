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
  { id: "privacy", label: "Privacy & Security", icon: "\uD83D\uDD12" },
  { id: "image-export", label: "Image Export", icon: "\uD83D\uDDBC" },
  { id: "memory", label: "Memory", icon: "\uD83E\uDDE0" },
  { id: "keyboard-shortcuts", label: "Keyboard Shortcuts", icon: "\u2328" },
  { id: "agent", label: "Agent Preferences", icon: "\uD83D\uDCAC", group: "Text", indent: true },
  { id: "user", label: "User Settings", icon: "\uD83D\uDCAC", group: "Text", indent: true },
  { id: "tts", label: "Text-to-Speech", icon: "\uD83D\uDCAC", group: "Text", indent: true },
  { id: "prompt-templates", label: "Prompt Templates", icon: "\uD83D\uDCAC", group: "Text", indent: true },
  { id: "appearance", label: "Theme", icon: "\u2699", group: "Miscellaneous", indent: true },
  { id: "sound", label: "Sound", icon: "\u2699", group: "Miscellaneous", indent: true },
  { id: "language", label: "Language", icon: "\u2699", group: "Miscellaneous", indent: true },
];

function getGroupEntries(
  entries: NavEntry[],
): { group: string; items: NavEntry[] }[] {
  const topLevel = entries.filter((e) => !e.group);
  const groups: Record<string, NavEntry[]> = {};
  for (const e of entries) {
    if (e.group) {
      if (!groups[e.group]) groups[e.group] = [];
      groups[e.group].push(e);
    }
  }
  const result: { group: string; items: NavEntry[] }[] = [
    { group: "", items: topLevel },
  ];
  for (const [group, items] of Object.entries(groups)) {
    result.push({ group, items });
  }
  return result;
}

export default function SettingsModal({
  onClose,
}: {
  onClose: () => void;
}) {
  const [activeSection, setActiveSection] = useState<SectionId>("privacy");

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

  const grouped = getGroupEntries(NAV_ENTRIES);

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
            className="text-light p-0"
            onClick={onClose}
            size="sm"
          >
            \u2715
          </Button>
        </div>
        <div className="settings-modal-body">
          <nav className="settings-nav">
            {grouped.map(({ group, items }) => (
              <div key={group || "__top"}>
                {group && (
                  <div className="settings-nav-group">{group}</div>
                )}
                {items.map((entry) => (
                  <button
                    key={entry.id}
                    className={
                      "settings-nav-item" +
                      (entry.indent ? " settings-nav-item-sub" : "") +
                      (activeSection === entry.id ? " active" : "")
                    }
                    onClick={() => setActiveSection(entry.id)}
                  >
                    <span>{entry.icon}</span>
                    <span>{entry.label}</span>
                  </button>
                ))}
              </div>
            ))}
          </nav>
          <div className="settings-content">{renderSection()}</div>
        </div>
      </div>
    </div>
  );
}
