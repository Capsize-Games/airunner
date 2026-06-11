// ── Action Menu Bar ──────────────────────────────────────────────────────
// Desktop-style menu bar anchored under the top header.  Each menu button
// opens a dropdown.  Actions propagate via window CustomEvents so that the
// menu bar (in Layout) can reach canvas state (inside CanvasProvider).
// ──────────────────────────────────────────────────────────────────────────
import {
  useState,
  useRef,
  useEffect,
  useCallback,
  type KeyboardEvent,
  type MouseEvent,
} from "react";
import {
  barStyle,
  menuBtnStyle,
  menuBtnActiveStyle,
  dropdownStyle,
} from "./styles";
import { dispatchMenuAction } from "./events";
import {
  MenuItemRow,
  type MenuGroup,
} from "./items";

export type { ActionMenuEvent } from "./events";
export { dispatchMenuAction, useMenuAction } from "./events";

export default function ActionMenuBar() {
  const [openMenu, setOpenMenu] = useState<string | null>(
    null,
  );
  const [hoveredSub, setHoveredSub] = useState<
    string | null
  >(null);
  const barRef = useRef<HTMLDivElement>(null);

  // ── Checkbox state ───────────────────────────────────────────────
  const [showChat, setShowChat] = useState(true);
  const [showCanvas, setShowCanvas] = useState(true);
  const [showCivitai, setShowCivitai] = useState(false);
  const [showRuler, setShowRuler] = useState(true);
  const [showGrid, setShowGrid] = useState(true);

  // Keep in sync with layout state via events
  useEffect(() => {
    const handler = (e: Event) => {
      const { detail } = e as CustomEvent<{
        showChat?: boolean;
        showCanvas?: boolean;
        showCivitai?: boolean;
      }>;
      if (detail.showChat !== undefined)
        setShowChat(detail.showChat);
      if (detail.showCanvas !== undefined)
        setShowCanvas(detail.showCanvas);
      if (detail.showCivitai !== undefined)
        setShowCivitai(detail.showCivitai);
    };
    window.addEventListener(
      "airunner:layout-state",
      handler,
    );
    return () =>
      window.removeEventListener(
        "airunner:layout-state",
        handler,
      );
  }, []);

  // Keep in sync with canvas state via events
  useEffect(() => {
    const handler = (e: Event) => {
      const { detail } = e as CustomEvent<{
        rulerShowRuler: boolean;
        gridShowGrid: boolean;
      }>;
      if (detail.rulerShowRuler !== undefined)
        setShowRuler(detail.rulerShowRuler);
      if (detail.gridShowGrid !== undefined)
        setShowGrid(detail.gridShowGrid);
    };
    window.addEventListener(
      "airunner:canvas-state",
      handler,
    );
    return () =>
      window.removeEventListener(
        "airunner:canvas-state",
        handler,
      );
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    if (!openMenu) return;
    const onDown = (e: globalThis.MouseEvent) => {
      if (
        barRef.current &&
        !barRef.current.contains(e.target as Node)
      ) {
        setOpenMenu(null);
        setHoveredSub(null);
      }
    };
    const timer = setTimeout(() => {
      window.addEventListener("mousedown", onDown);
    }, 0);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("mousedown", onDown);
    };
  }, [openMenu]);

  const toggleMenu = useCallback(
    (label: string) => {
      setOpenMenu((prev) =>
        prev === label ? null : label,
      );
      setHoveredSub(null);
    },
    [],
  );

  const closeAll = useCallback(() => {
    setOpenMenu(null);
    setHoveredSub(null);
  }, []);

  // ── Menu definitions ─────────────────────────────────────────────
  const menus: MenuGroup[] = [
    {
      label: "File",
      items: [
        {
          type: "action" as const,
          label: "New Canvas",
          action: "file:new-document",
          disabled: !showCanvas,
        },
      ],
    },
    {
      label: "Edit",
      items: [
        {
          type: "action" as const,
          label: "Undo",
          action: "edit:undo",
          icon: "undo-2",
          shortcut: "Ctrl+Z",
          disabled: !showCanvas,
        },
        {
          type: "action" as const,
          label: "Redo",
          action: "edit:redo",
          icon: "redo-2",
          shortcut: "Ctrl+Y",
          disabled: !showCanvas,
        },
        { type: "divider" as const },
        {
          type: "action" as const,
          label: "Cut",
          action: "edit:cut",
          icon: "scissors",
          shortcut: "Ctrl+X",
          disabled: !showCanvas,
        },
        {
          type: "action" as const,
          label: "Copy",
          action: "edit:copy",
          icon: "copy",
          shortcut: "Ctrl+C",
          disabled: !showCanvas,
        },
        {
          type: "action" as const,
          label: "Paste",
          action: "edit:paste",
          icon: "clipboard",
          shortcut: "Ctrl+P",
          disabled: !showCanvas,
        },
        {
          type: "action" as const,
          label: "Delete",
          action: "edit:delete",
          icon: "trash-2",
          shortcut: "Del",
          disabled: !showCanvas,
        },
      ],
    },
    {
      label: "Select",
      items: [
        {
          type: "action" as const,
          label: "All",
          action: "select:all",
          shortcut: "Ctrl+A",
          disabled: !showCanvas,
        },
        {
          type: "action" as const,
          label: "None",
          action: "select:none",
          shortcut: "Ctrl+Shift+A",
          disabled: !showCanvas,
        },
      ],
    },
    {
      label: "View",
      items: [
        {
          type: "checkbox" as const,
          label: "Chat",
          action: "view:toggle-chat",
          checked: showChat,
          onToggle: () => {
            const next = !showChat;
            setShowChat(next);
            dispatchMenuAction({
              type: "view:toggle-chat",
            });
          },
        },
        {
          type: "checkbox" as const,
          label: "Canvas",
          action: "view:toggle-canvas",
          checked: showCanvas,
          onToggle: () => {
            setShowCanvas(!showCanvas);
            dispatchMenuAction({
              type: "view:toggle-canvas",
            });
          },
        },
        {
          type: "checkbox" as const,
          label: "CivitAI",
          action: "view:toggle-civitai",
          checked: showCivitai,
          onToggle: () => {
            setShowCivitai(!showCivitai);
            dispatchMenuAction({
              type: "view:toggle-civitai",
            });
          },
        },
        { type: "divider" as const },
        {
          type: "checkbox" as const,
          label: "Show Ruler",
          action: "view:toggle-ruler",
          checked: showRuler,
          onToggle: () => {
            const next = !showRuler;
            setShowRuler(next);
            dispatchMenuAction({
              type: "view:toggle-ruler",
            });
          },
          disabled: !showCanvas,
        },
        {
          type: "checkbox" as const,
          label: "Show Grid",
          action: "view:toggle-grid",
          checked: showGrid,
          onToggle: () => {
            const next = !showGrid;
            setShowGrid(next);
            dispatchMenuAction({
              type: "view:toggle-grid",
            });
          },
          disabled: !showCanvas,
        },
      ],
    },
  ];

  return (
    <div
      ref={barRef}
      style={barStyle}
      role="menubar"
      onKeyDown={(e: KeyboardEvent<HTMLDivElement>) => {
        if (e.key === "Escape") closeAll();
      }}
    >
      {menus.map((group) => (
        <div
          key={group.label}
          style={{ position: "relative" }}
        >
          <button
            style={
              openMenu === group.label
                ? menuBtnActiveStyle
                : menuBtnStyle
            }
            onClick={() => toggleMenu(group.label)}
            onMouseEnter={(
              e: MouseEvent<HTMLButtonElement>,
            ) => {
              if (openMenu !== null) {
                setOpenMenu(group.label);
                setHoveredSub(null);
              }
              e.currentTarget.style.color = "#fff";
            }}
            onMouseLeave={(
              e: MouseEvent<HTMLButtonElement>,
            ) => {
              if (openMenu !== group.label) {
                e.currentTarget.style.color =
                  "rgba(255,255,255,0.65)";
              }
            }}
            role="menuitem"
            aria-haspopup
            aria-expanded={openMenu === group.label}
          >
            {group.label}
          </button>

          {openMenu === group.label && (
            <div style={dropdownStyle} role="menu">
              {group.items.map((entry, i) => (
                <MenuItemRow
                  key={i}
                  entry={entry}
                  onClose={closeAll}
                  onHover={setHoveredSub}
                  hoveredSub={hoveredSub}
                />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
