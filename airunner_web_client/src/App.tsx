import { Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import ChatView from "./components/chat/ChatView";
import ArtView from "./components/art/ArtView";
import SettingsView from "./components/settings/SettingsView";
import DocumentsView from "./components/documents/DocumentsView";
import DownloadManager from "./components/downloads/DownloadManager";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ChatView />} />
        <Route path="/chat" element={<ChatView />} />
        <Route path="/art" element={<ArtView />} />
        <Route path="/settings" element={<SettingsView />} />
        <Route path="/documents" element={<DocumentsView />} />
        <Route path="/downloads" element={<DownloadManager />} />
      </Routes>
    </Layout>
  );
}
