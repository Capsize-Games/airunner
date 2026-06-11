// ── Action Menu Item Components ─────────────────────────────────────────
import type { MouseEvent } from "react";
import LucideIcon from "../../shared/LucideIcon";
import {
  menuItemStyle,
  checkboxItemStyle,
  submenuArrow,
  submenuWrapperStyle,
  checkMarkStyle,
  dividerStyle,
  shortcutStyle,
} from "./styles";
import type { ActionMenuEvent } from "./events";
import { dispatchMenuAction } from "./events";

// ── Menu data types ─────────────────────────────────────────────────────

export interface MenuAction {
  type: "action";
  label: string;
  action: ActionMenuEvent["type"];
  icon?: string;
  shortcut?: string;
  disabled?: boolean;
}

export interface MenuCheckbox {
  type: "checkbox";
  label: string;
  action: ActionMenuEvent["type"];
  checked: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export interface MenuSubmenu {
  type: "submenu";
  label: string;
  items: MenuEntry[];
}

export interface MenuDivider {
  type: "divider";
}

export type MenuEntry =
  | MenuAction
  | MenuCheckbox
  | MenuSubmenu
  | MenuDivider;

export interface MenuGroup {
  label: string;
  items: MenuEntry[];
}

// ── Subcomponents ───────────────────────────────────────────────────────

function CheckIcon({ checked }: { checked: boolean }) {
  return (
    <span style={checkMarkStyle}>
      {checked ? "\u2713" : ""}
    </span>
  );
}

export function SubMenuItemRow({
  entry,
  onClose,
}: {
  entry: MenuEntry;
  onClose: () => void;
}) {
  if (entry.type === "submenu") return null;

  if (entry.type === "divider") {
    return <div style={dividerStyle} />;
  }

  const isDisabled =
    "disabled" in entry ? entry.disabled : false;

  if (entry.type === "checkbox") {
    return (
      <button
        disabled={isDisabled}
        style={{
          ...checkboxItemStyle,
          opacity: isDisabled ? 0.4 : 1,
          cursor: isDisabled ? "default" : "pointer",
        }}
        onMouseEnter={(
          e: MouseEvent<HTMLButtonElement>,
        ) => {
          if (isDisabled) return;
          e.currentTarget.style.background =
            "rgba(99,153,255,0.12)";
        }}
        onMouseLeave={(
          e: MouseEvent<HTMLButtonElement>,
        ) => {
          if (isDisabled) return;
          e.currentTarget.style.background =
            "transparent";
        }}
        onClick={() => {
          if (isDisabled) return;
          entry.onToggle();
          onClose();
        }}
      >
        <CheckIcon checked={entry.checked} />
        <span style={{ flex: 1 }}>{entry.label}</span>
      </button>
    );
  }

  return (
    <button
      disabled={isDisabled}
      style={{
        ...menuItemStyle,
        opacity: isDisabled ? 0.4 : 1,
        cursor: isDisabled ? "default" : "pointer",
      }}
      onMouseEnter={(
        e: MouseEvent<HTMLButtonElement>,
      ) => {
        if (isDisabled) return;
        e.currentTarget.style.background =
          "rgba(99,153,255,0.12)";
      }}
      onMouseLeave={(
        e: MouseEvent<HTMLButtonElement>,
      ) => {
        if (isDisabled) return;
        e.currentTarget.style.background =
          "transparent";
      }}
      onClick={() => {
        if (isDisabled) return;
        dispatchMenuAction({ type: entry.action });
        onClose();
      }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {entry.icon && (
          <LucideIcon
            name={entry.icon}
            size={13}
            className="text-theme-secondary"
          />
        )}
        <span>{entry.label}</span>
      </span>
      {entry.shortcut && (
        <span style={shortcutStyle}>
          {entry.shortcut}
        </span>
      )}
    </button>
  );
}

export function MenuItemRow({
  entry,
  onClose,
  onHover,
  hoveredSub,
}: {
  entry: MenuEntry;
  onClose: () => void;
  onHover: (label: string | null) => void;
  hoveredSub: string | null;
}) {
  if (entry.type === "divider") {
    return <div style={dividerStyle} />;
  }

  if (entry.type === "submenu") {
    const open = hoveredSub === entry.label;
    return (
      <div
        style={{
          ...menuItemStyle,
          background: open
            ? "rgba(99,153,255,0.12)"
            : "transparent",
          position: "relative",
        }}
        onMouseEnter={() => onHover(entry.label)}
        onMouseLeave={() => onHover(null)}
      >
        <span>{entry.label}</span>
        <span style={submenuArrow}>&#9654;</span>
        {open && (
          <div style={submenuWrapperStyle}>
            {entry.items.map((child, ci) => (
              <SubMenuItemRow
                key={ci}
                entry={child}
                onClose={onClose}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return <SubMenuItemRow entry={entry} onClose={onClose} />;
}
