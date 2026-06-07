import { useCallback, useState, lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import ChatView from "./components/chat/ChatView";
import ArtView from "./components/art/ArtView";
import SettingsModal from "./components/settings/SettingsModal";
import { useLayoutPrefs, type PanelId } from "./hooks/useLayoutPrefs";
import {
  extensionRouteElements,
  extensionProviders,
} from "virtual:extensions";

const CacheDebugPanel = lazy(
  () => import("./components/shared/CacheDebugPanel"),
);

const showDebugPanel =
  import.meta.env.DEV ||
  (typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).has("debug"));

export default function App() {
  const {
    showChat,
    setShowChat,
    showCanvas,
    setShowCanvas,
    ttsOn,
    setTtsOn,
    sttOn,
    setSttOn,
    leftPanel,
    setLeftPanel,
    rightPanel,
    setRightPanel,
    conversationId,
    setConversationId,
  } = useLayoutPrefs();

  const [showSettings, setShowSettings] = useState(false);
  const [showCacheDebug, setShowCacheDebug] = useState(false);

  const handleSelectConversation = useCallback(
    (id: number) => {
      setConversationId(id);
    },
    [setConversationId],
  );

  const handleToggleCacheDebug = useCallback(() => {
    setShowCacheDebug((v) => !v);
  }, []);

  // Compose extension providers (empty in core, populated in fork)
  const Providers = extensionProviders.reduce(
    (Acc, Provider) =>
      ({ children }: { children: React.ReactNode }) =>
        (
          <Acc>
            <Provider>{children}</Provider>
          </Acc>
        ),
    ({ children }: { children: React.ReactNode }) => <>{children}</>,
  );

  return (
    <Providers>
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
        <Route
          path="/chat"
          element={<ChatView conversationId={conversationId} />}
        />
        <Route path="/art" element={<ArtView />} />
        <Route
          path="/settings"
          element={
            <SettingsModal onClose={() => window.history.back()} />
          }
        />
        {/* Extension route elements — empty array in core, populated in fork */}
        {extensionRouteElements}
      </Routes>

      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}

      {showCacheDebug && (
        <Suspense fallback={null}>
          <CacheDebugPanel />
        </Suspense>
      )}
    </Providers>
  );
}
