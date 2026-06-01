import { useState } from "react";
import Layout from "./components/layout/Layout";
import ChatView from "./components/chat/ChatView";
import ArtView from "./components/art/ArtView";
import SettingsView from "./components/settings/SettingsView";
import DocumentsView from "./components/documents/DocumentsView";
import DownloadManager from "./components/downloads/DownloadManager";

type Tab =
  | "chat"
  | "art"
  | "settings"
  | "documents"
  | "downloads";

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const [leftPanel, setLeftPanel] = useState<string | null>(null);
  const [rightPanel, setRightPanel] = useState<string | null>(null);
  const [artSidebar, setArtSidebar] = useState(false);

  const renderContent = () => {
    switch (tab) {
      case "chat":   return <ChatView />;
      case "art":    return <ArtView />;
      case "settings": return <SettingsView />;
      case "documents": return <DocumentsView />;
      case "downloads": return <DownloadManager />;
    }
  };

  return (
    <Layout
      activeTab={tab}
      onTab={setTab}
      leftPanel={leftPanel}
      onLeftPanel={setLeftPanel}
      rightPanel={rightPanel}
      onRightPanel={setRightPanel}
      artSidebar={artSidebar}
      onArtSidebar={setArtSidebar}
    >
      {renderContent()}
    </Layout>
  );
}
