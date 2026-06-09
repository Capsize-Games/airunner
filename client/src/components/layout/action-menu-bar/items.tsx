// ── Action Menu Item Components ─────────────────────────────────────────
import type { MouseEvent } from "react";
import {
  menuItemStyle,
  checkboxItemStyle,
  submenuArrow,
  submenuWrapperStyle,
  checkMarkStyle,
  dividerStyle,
} from "./styles";
import type { ActionMenuEvent } from "./events";
import { dispatchMenuAction } from "./events";

// ── Menu data types ─────────────────────────────────────────────────────

export interface MenuAction {
  type: "action";
  label: string;
  action: ActionMenuEvent["type"];
}

export interface MenuCheckbox {
  type: "checkbox";
  label: string;
  action: ActionMenuEvent["type"];
  checked: boolean;
  onToggle: () => void;
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

  if (entry.type === "checkbox") {
    return (
      <button
        style={checkboxItemStyle}
        onMouseEnter={(
          e: MouseEvent<HTMLButtonElement>,
        ) => {
          e.currentTarget.style.background =
            "rgba(99,153,255,0.12)";
        }}
        onMouseLeave={(
          e: MouseEvent<HTMLButtonElement>,
        ) => {
          e.currentTarget.style.background =
            "transparent";
        }}
        onClick={() => {
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
      style={menuItemStyle}
      onMouseEnter={(e: MouseEvent<HTMLButtonElement>) => {
        e.currentTarget.style.background =
          "rgba(99,153,255,0.12)";
      }}
      onMouseLeave={(e: MouseEvent<HTMLButtonElement>) => {
        e.currentTarget.style.background = "transparent";
      }}
      onClick={() => {
        dispatchMenuAction({ type: entry.action });
        onClose();
      }}
    >
      <span>{entry.label}</span>
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
