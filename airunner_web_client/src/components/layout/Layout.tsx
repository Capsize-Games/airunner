import type { ReactNode, Dispatch, SetStateAction } from "react";

type Tab = "chat" | "art" | "settings" | "documents" | "downloads";

interface LayoutProps {
  children: ReactNode;
  activeTab: Tab;
  onTab: Dispatch<SetStateAction<Tab>>;
  leftPanel: string | null;
  onLeftPanel: Dispatch<SetStateAction<string | null>>;
  rightPanel: string | null;
  onRightPanel: Dispatch<SetStateAction<string | null>>;
  artSidebar: boolean;
  onArtSidebar: Dispatch<SetStateAction<boolean>>;
}

const icon = (name: string) =>
  `/icons/lucide/dark/${name}.svg`;

export default function Layout({
  children,
  activeTab,
  onTab,
  leftPanel,
  onLeftPanel,
  rightPanel,
  onRightPanel,
  artSidebar,
  onArtSidebar,
}: LayoutProps) {
  const toggleLeft = (name: string) =>
    onLeftPanel((p) => (p === name ? null : name));

  const toggleRight = (name: string) =>
    onRightPanel((p) => (p === name ? null : name));

  return (
    <div className="app-shell">
      {/* ─── Left bar ─── */}
      <div className="left-bar">
        <button
          className={activeTab === "chat" ? "active" : ""}
          onClick={() => onTab("chat")}
          title="Chat"
        >
          <img src={icon("message-circle")} alt="Chat" />
        </button>
        <button
          className={activeTab === "art" ? "active" : ""}
          onClick={() => onTab("art")}
          title="Art"
        >
          <img src={icon("paintbrush-vertical")} alt="Art" />
        </button>
        <button
          className={leftPanel === "history" ? "active" : ""}
          onClick={() => toggleLeft("history")}
          title="History"
        >
          <img src={icon("history")} alt="History" />
        </button>
        <button
          className={leftPanel === "settings" ? "active" : ""}
          onClick={() => toggleLeft("settings")}
          title="LLM Settings"
        >
          <img src={icon("settings-2")} alt="Settings" />
        </button>
        <div style={{ flex: 1 }} />
        <button
          className={activeTab === "documents" ? "active" : ""}
          onClick={() => onTab("documents")}
          title="Documents"
        >
          <img src={icon("folder-open")} alt="Documents" />
        </button>
        <button
          className={activeTab === "downloads" ? "active" : ""}
          onClick={() => onTab("downloads")}
          title="Downloads"
        >
          <img src={icon("download")} alt="Downloads" />
        </button>
      </div>

      {/* ─── Left collapsible panel ─── */}
      <div className={leftPanel ? "panel panel-left" : "panel-collapsed"}>
        {leftPanel === "history" && (
          <div className="p-2">
            <h6>Conversation History</h6>
            {/* Sidebar conversations list will render here in future update */}
          </div>
        )}
        {leftPanel === "settings" && (
          <div className="p-2">
            <h6>LLM Settings</h6>
          </div>
        )}
      </div>

      {/* ─── Center (chat + optional art sidebar) ─── */}
      <div className="center-area">
        <div className="panel chat-panel d-flex flex-column">
          {children}
        </div>

        {artSidebar && (
          <div className="panel art-panel p-2">
            <h6>Art Generator</h6>
            {/* Art form will render here */}
          </div>
        )}
      </div>

      {/* ─── Right panel ─── */}
      <div className={rightPanel ? "panel panel-right" : "panel-collapsed"}>
        {rightPanel === "stats" && (
          <div className="p-2">
            <h6>Model Resources</h6>
          </div>
        )}
      </div>

      {/* ─── Right bar ─── */}
      <div className="right-bar">
        <button
          className={rightPanel === "stats" ? "active" : ""}
          onClick={() => toggleRight("stats")}
          title="Model Resources"
        >
          <img src={icon("bar-chart-3")} alt="Stats" />
        </button>
        <button
          className={artSidebar ? "active" : ""}
          onClick={() => onArtSidebar((s) => !s)}
          title="Art Prompt"
        >
          <img src={icon("paintbrush-vertical")} alt="Art Prompt" />
        </button>
        <button
          onClick={() => toggleRight("none")}
          title="Settings"
        >
          <img src={icon("settings")} alt="Settings" />
        </button>
        <div style={{ flex: 1 }} />
        <button
          onClick={() => onTab("settings")}
          title="Settings"
        >
          <img src={icon("info")} alt="About" />
        </button>
      </div>
    </div>
  );
}
