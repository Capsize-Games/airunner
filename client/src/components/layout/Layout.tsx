// ── Layout ──────────────────────────────────────────────────────────────
import {
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import CanvasPanel from "../panels/CanvasPanel";
import CivitaiBrowserPanel from "../panels/civitai-browser/CivitaiBrowserPanel";
import DownloadTray from "../downloads/DownloadTray";
import TopBar from "./TopBar";
import { LeftIconBar } from "./IconBar";
import { CanvasProvider } from "../../features/canvas";
import WelcomeScreen from "./WelcomeScreen";
import FooterStats from "./FooterStats";
import LiveIndicator from "./LiveIndicator";
import { useMenuAction } from "./action-menu-bar";

const HANDLE_W = 4;
const CHAT_MIN = 260;
const CANVAS_MIN = 400;

type PanelId = "civitai_browser";

interface LayoutProps {
  children: ReactNode;
  rightPanel: PanelId | null;
  onRightPanel: (id: PanelId) => void;
  showChat: boolean;
  onToggleChat: () => void;
  showCanvas: boolean;
  onToggleCanvas: () => void;
  onOpenSettings: () => void;
  onSelectConversation: (id: number) => void;
  bottomBarSlot?: React.ReactNode;
}

function saveNum(key: string, val: number) {
  try {
    localStorage.setItem(key, String(val));
  } catch {
    /* */
  }
}

function loadNum(
  key: string,
  fallback: number,
): number {
  try {
    const v = localStorage.getItem(key);
    return v !== null ? Number(v) : fallback;
  } catch {
    return fallback;
  }
}

/* ── Drag state (module-level, captured at mousedown) ── */
let dragState: {
  startX: number;
  startChatW: number;
  maxChatW: number;
  setChatW: (w: number) => void;
} | null = null;

function onGlobalMouseMove(e: MouseEvent) {
  if (!dragState) return;
  const delta = e.clientX - dragState.startX;
  dragState.setChatW(
    Math.max(
      CHAT_MIN,
      Math.min(
        dragState.maxChatW,
        dragState.startChatW + delta,
      ),
    ),
  );
}

function onGlobalMouseUp() {
  if (!dragState) return;
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  dragState = null;
}

if (typeof window !== "undefined") {
  window.addEventListener(
    "mousemove",
    onGlobalMouseMove,
  );
  window.addEventListener("mouseup", onGlobalMouseUp);
}

export default function Layout({
  children,
  rightPanel,
  onRightPanel,
  showChat,
  onToggleChat,
  showCanvas,
  onToggleCanvas,
  onOpenSettings,
  onSelectConversation: _onSelectConversation,
  bottomBarSlot,
}: LayoutProps) {
  const panelsRef = useRef<HTMLDivElement>(null);
  const [panelsWidth, setPanelsWidth] = useState(0);

  useEffect(() => {
    const el = panelsRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries)
        setPanelsWidth(entry.contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const [chatW, setChatW] = useState(() =>
    loadNum("airunner_chat_w", 400),
  );

  // Clamp chat width when container or visibility changes.
  useEffect(() => {
    if (panelsWidth === 0 || !showChat) return;
    const max =
      panelsWidth -
      (showCanvas ? CANVAS_MIN + HANDLE_W : 0);
    if (chatW > max) setChatW(Math.max(CHAT_MIN, max));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [panelsWidth, showChat, showCanvas]);

  useEffect(
    () => saveNum("airunner_chat_w", chatW),
    [chatW],
  );

  // ── Respond to action-menu events ──────────────────────────────────
  useMenuAction(
    useCallback(
      (action) => {
        switch (action.type) {
          case "view:toggle-chat":
            onToggleChat();
            break;
          case "view:toggle-canvas":
            onToggleCanvas();
            break;
          case "view:toggle-civitai":
            onRightPanel("civitai_browser");
            break;
        }
      },
      [
        onToggleChat,
        onToggleCanvas,
        onRightPanel,
        rightPanel,
      ],
    ),
  );

  // Sync layout panel state back to the action menu bar
  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("airunner:layout-state", {
        detail: {
          showChat,
          showCanvas:
            showCanvas &&
            rightPanel !== "civitai_browser",
          showCivitai:
            rightPanel === "civitai_browser",
        },
      }),
    );
  }, [showChat, showCanvas, rightPanel]);

  const makeHandle = () => {
    const onDown = (e: React.MouseEvent) => {
      e.preventDefault();
      dragState = {
        startX: e.clientX,
        startChatW: chatW,
        maxChatW:
          panelsWidth - CANVAS_MIN - HANDLE_W,
        setChatW,
      };
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    };
    return (
      <div
        className="resize-handle"
        onMouseDown={onDown}
      />
    );
  };

  return (
    <div className="app-shell">
      <TopBar />

      <div className="main-row">
        <LeftIconBar
          showChat={showChat}
          showCanvas={showCanvas}
          rightPanel={rightPanel}
          onToggleChat={onToggleChat}
          onToggleCanvas={onToggleCanvas}
          onRightPanel={onRightPanel}
          onOpenSettings={onOpenSettings}
          bottomSlot={bottomBarSlot}
        />

        {/* ── Panels container ── */}
        <div
          ref={panelsRef}
          className="flex-grow-1 d-flex overflow-hidden min-w-0"
        >
          {/* Chat */}
          {showChat && (
            <div
              className="chat-panel"
              style={
                showCanvas
                  ? {
                      width: chatW,
                      flex: "none",
                      overflow: "hidden",
                    }
                  : {
                      flex: 1,
                      minWidth: 0,
                      overflow: "hidden",
                    }
              }
            >
              {children}
            </div>
          )}

          {showChat && showCanvas && makeHandle()}

          {/* Main content */}
          {showCanvas && (
            <div
              className="flex-grow-1 overflow-hidden min-w-0"
            >
              {rightPanel === "civitai_browser" ? (
                <CivitaiBrowserPanel />
              ) : (
                <CanvasProvider>
                  <CanvasPanel />
                </CanvasProvider>
              )}
            </div>
          )}

          {/* Welcome screen */}
          {!showChat && !showCanvas && (
            <WelcomeScreen
              onOpenChat={onToggleChat}
              onOpenCanvas={onToggleCanvas}
              onOpenCivitai={() =>
                onRightPanel("civitai_browser")
              }
            />
          )}
        </div>
      </div>

      <DownloadTray />

      <div
        className="footer-bar d-flex justify-content-between align-items-center"
        style={{ padding: "0 12px" }}
      >
        <span>
          &copy; {new Date().getFullYear()} Capsize
          LLC &mdash; All rights reserved.
        </span>
        <div
          className="d-flex align-items-center"
          style={{ gap: 12 }}
        >
          <FooterStats />
          <LiveIndicator />
        </div>
      </div>
    </div>
  );
}
