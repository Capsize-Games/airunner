import {
  useCallback,
  useState,
  lazy,
  Suspense,
  type ReactNode,
} from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/layout/Layout";
import ChatView from "./components/chat/ChatView";
import ArtView from "./components/art/ArtView";
import SettingsModal from "./components/settings/SettingsModal";
import { useLayoutPrefs, type PanelId } from "./hooks/useLayoutPrefs";
import { useMemo } from "react";
import {
  extensionRouteElements,
  extensionProviders,
  extensionBottomBarItems,
} from "virtual:extensions";

const CacheDebugPanel = lazy(
  () => import("./components/shared/CacheDebugPanel"),
);

const StatsPanel = lazy(
  () => import("./components/panels/StatsPanel"),
);

const showDebugPanel =
  import.meta.env.DEV ||
  (typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).has("debug"));

const overlayContainerStyle: React.CSSProperties = {
  position: "fixed",
  bottom: 40,
  right: 56,
  display: "flex",
  gap: 12,
  flexDirection: "row-reverse",
  zIndex: 9999,
};

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
    rightPanel,
    setRightPanel,
    conversationId,
    setConversationId,
  } = useLayoutPrefs();

  const [showSettings, setShowSettings] = useState(false);
  const [showCacheDebug, setShowCacheDebug] = useState(false);
  const [showStats, setShowStats] = useState(false);

  const handleSelectConversation = useCallback(
    (id: number) => {
      setConversationId(id);
    },
    [setConversationId],
  );

  const handleToggleCacheDebug = useCallback(() => {
    setShowCacheDebug((v) => !v);
  }, []);

  const handleToggleStats = useCallback(() => {
    setShowStats((v) => !v);
  }, []);

  // Compose extension providers (empty in core, populated in fork).
  // useMemo prevents the wrapper component from being recreated on every
  // render, which would force all children (including AuthProvider) to
  // unmount and remount — causing a "Signing in…" flash.
  const Providers = useMemo(
    () =>
      extensionProviders.reduce(
        (Acc, Provider) =>
          ({ children }: { children: ReactNode }) =>
            (
              <Acc>
                <Provider>{children}</Provider>
              </Acc>
            ),
        ({ children }: { children: ReactNode }) => <>{children}</>,
      ),
    [],
  );

  return (
    <Providers>
      <Routes>
        <Route
          path="/"
          element={
            <Layout
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
              showStats={showStats}
              onToggleStats={handleToggleStats}
              bottomBarSlot={extensionBottomBarItems}
            >
              {showChat && <ChatView
                conversationId={conversationId}
                onSelectConversation={handleSelectConversation}
              />}
            </Layout>
          }
        />
        <Route
          path="/chat"
          element={<ChatView
            conversationId={conversationId}
            onSelectConversation={handleSelectConversation}
          />}
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

      {(showCacheDebug || showStats) && (
        <div style={overlayContainerStyle}>
          {showCacheDebug && (
            <Suspense fallback={null}>
              <CacheDebugPanel />
            </Suspense>
          )}
          {showStats && (
            <Suspense fallback={null}>
              <StatsPanel />
            </Suspense>
          )}
        </div>
      )}
    </Providers>
  );
}
