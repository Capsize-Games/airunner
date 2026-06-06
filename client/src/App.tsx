import { useCallback, useState, lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import ChatView from "./components/chat/ChatView";
import ArtView from "./components/art/ArtView";
import SettingsModal from "./components/settings/SettingsModal";
import { useLayoutPrefs, type PanelId } from "./hooks/useLayoutPrefs";

const CacheDebugPanel = lazy(
  () => import("./components/shared/CacheDebugPanel"),
);

const showDebugPanel =
  import.meta.env.DEV ||
  (typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).has("debug"));

export default function App() {
  const {
    showChat, setShowChat,
    showCanvas, setShowCanvas,
    ttsOn, setTtsOn,
    sttOn, setSttOn,
    leftPanel, setLeftPanel,
    rightPanel, setRightPanel,
    conversationId, setConversationId,
  } = useLayoutPrefs();

  const [showSettings, setShowSettings] = useState(false);
  const [showCacheDebug, setShowCacheDebug] = useState(false);

  const handleSelectConversation = useCallback((id: number) => {
    setConversationId(id);
  }, [setConversationId]);

  const handleToggleCacheDebug = useCallback(() => {
    setShowCacheDebug((v) => !v);
  }, []);

  return (
    <>
      <Routes>
        <Route
          path="/"
          element={
            <Layout
              leftPanel={leftPanel}
              onLeftPanel={(id: PanelId) =>
                setLeftPanel(leftPanel === id ? null : id)
              }
              rightPanel={rightPanel}
              onRightPanel={(id: PanelId) =>
                setRightPanel(rightPanel === id ? null : id)
              }
              showChat={showChat}
              onToggleChat={() => setShowChat(!showChat)}
              showCanvas={showCanvas}
              onToggleCanvas={() => setShowCanvas(!showCanvas)}
              ttsOn={ttsOn}
              onToggleTts={() => setTtsOn(!ttsOn)}
              sttOn={sttOn}
              onToggleStt={() => setSttOn(!sttOn)}
              onOpenSettings={() => setShowSettings(true)}
              onSelectConversation={handleSelectConversation}
              showCacheDebug={showCacheDebug}
              onToggleCacheDebug={handleToggleCacheDebug}
            >
              {showChat && <ChatView conversationId={conversationId} />}
            </Layout>
          }
        />
        <Route path="/chat" element={<ChatView conversationId={conversationId} />} />
        <Route path="/art" element={<ArtView />} />
        <Route
          path="/settings"
          element={
            <SettingsModal onClose={() => window.history.back()} />
          }
        />
      </Routes>

      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}

      {showCacheDebug && (
        <Suspense fallback={null}>
          <CacheDebugPanel />
        </Suspense>
      )}
    </>
  );
}
