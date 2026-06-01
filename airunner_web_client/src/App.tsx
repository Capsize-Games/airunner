import { useState } from "react";
import Layout from "./components/layout/Layout";
import ChatView from "./components/chat/ChatView";
import SettingsModal from "./components/settings/SettingsModal";

type PanelId =
  | "knowledge"
  | "history"
  | "llm_settings"
  | "art_model"
  | "lora"
  | "embeddings"
  | "layers"
  | "grid"
  | "image_browser"
  | "stats";

export default function App() {
  const [showCanvas, setShowCanvas] = useState(false);
  const [showArtPrompt, setShowArtPrompt] = useState(false);
  const [ttsOn, setTtsOn] = useState(false);
  const [sttOn, setSttOn] = useState(false);
  const [leftPanel, setLeftPanel] = useState<PanelId | null>(null);
  const [rightPanel, setRightPanel] = useState<PanelId | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  return (
    <>
      <Layout
        leftPanel={leftPanel}
        onLeftPanel={(id: PanelId) =>
          setLeftPanel((prev) => (prev === id ? null : id))
        }
        rightPanel={rightPanel}
        onRightPanel={(id: PanelId) =>
          setRightPanel((prev) => (prev === id ? null : id))
        }
        showCanvas={showCanvas}
        onToggleCanvas={() => setShowCanvas((s) => !s)}
        showArtPrompt={showArtPrompt}
        onToggleArtPrompt={() => setShowArtPrompt((s) => !s)}
        ttsOn={ttsOn}
        onToggleTts={() => setTtsOn((s) => !s)}
        sttOn={sttOn}
        onToggleStt={() => setSttOn((s) => !s)}
        onOpenSettings={() => setShowSettings(true)}
      >
        <ChatView />
      </Layout>

      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </>
  );
}
