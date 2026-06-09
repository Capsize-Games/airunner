import {
  useCallback,
  useState,
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


  const handleSelectConversation = useCallback(
    (id: number) => {
      setConversationId(id);
    },
    [setConversationId],
  );

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
              onRightPanel={(id: PanelId) => {
                if (rightPanel !== id) {
                  setShowCanvas(true);
                } else {
                  setShowCanvas(false);
                }
                setRightPanel(
                  rightPanel === id ? null : id,
                );
              }}
              showChat={showChat}
              onToggleChat={() => setShowChat(!showChat)}
              showCanvas={showCanvas}
              onToggleCanvas={() => {
                if (rightPanel === "civitai_browser") {
                  setRightPanel(null);
                } else {
                  setShowCanvas(!showCanvas);
                }
              }}
              onOpenSettings={() => setShowSettings(true)}
              onSelectConversation={handleSelectConversation}
              bottomBarSlot={extensionBottomBarItems}
            >
              {showChat && <ChatView
                conversationId={conversationId}
                onSelectConversation={handleSelectConversation}
                ttsOn={ttsOn}
                onToggleTts={() => setTtsOn(!ttsOn)}
                sttOn={sttOn}
                onToggleStt={() => setSttOn(!sttOn)}
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

    </Providers>
  );
}
