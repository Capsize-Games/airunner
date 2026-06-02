import { useState, useCallback } from "react";
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
  | "stats"
  | "civitai_browser";

function loadBool(key: string, fallback: boolean): boolean {
  try {
    const v = localStorage.getItem(key);
    return v !== null ? v === "true" : fallback;
  } catch {
    return fallback;
  }
}

function loadString(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function loadNum(key: string, fallback: number): number {
  try {
    const v = localStorage.getItem(key);
    return v !== null ? Number(v) : fallback;
  } catch {
    return fallback;
  }
}

function persist(key: string, value: unknown) {
  try {
    localStorage.setItem(key, String(value));
  } catch { /* */ }
}

export default function App() {
  const [showChat, setShowChat] = useState(() =>
    loadBool("airunner_show_chat", true),
  );
  const [showCanvas, setShowCanvas] = useState(() =>
    loadBool("airunner_show_canvas", false),
  );
  const [showArtPrompt, setShowArtPrompt] = useState(() =>
    loadBool("airunner_show_art_prompt", false),
  );
  const [ttsOn, setTtsOn] = useState(() =>
    loadBool("airunner_tts_on", false),
  );
  const [sttOn, setSttOn] = useState(() =>
    loadBool("airunner_stt_on", false),
  );
  const [leftPanel, setLeftPanel] = useState<PanelId | null>(() => {
    const v = loadString("airunner_left_panel", "");
    return (v as PanelId) || null;
  });
  const [rightPanel, setRightPanel] = useState<PanelId | null>(() => {
    const v = loadString("airunner_right_panel", "");
    return (v as PanelId) || null;
  });
  const [showSettings, setShowSettings] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(
    () => {
      const v = loadNum("airunner_conversation_id", 0);
      return v > 0 ? v : null;
    },
  );

  const makeToggle = useCallback(
    (key: string, next: boolean, setter: (val: boolean) => void) =>
      () => {
        persist(key, next);
        setter(next);
      },
    [],
  );

  const handleSelectConversation = useCallback((id: number) => {
    setConversationId(id);
    persist("airunner_conversation_id", id);
  }, []);

  return (
    <>
      <Layout
        leftPanel={leftPanel}
        onLeftPanel={(id: PanelId) =>
          setLeftPanel((prev) => {
            const next = prev === id ? null : id;
            persist("airunner_left_panel", next ?? "");
            return next;
          })
        }
        rightPanel={rightPanel}
        onRightPanel={(id: PanelId) =>
          setRightPanel((prev) => {
            const next = prev === id ? null : id;
            persist("airunner_right_panel", next ?? "");
            return next;
          })
        }
        showChat={showChat}
        onToggleChat={() =>
          setShowChat((s) => {
            persist("airunner_show_chat", !s);
            return !s;
          })
        }
        showCanvas={showCanvas}
        onToggleCanvas={makeToggle(
          "airunner_show_canvas",
          !showCanvas,
          setShowCanvas,
        )}
        showArtPrompt={showArtPrompt}
        onToggleArtPrompt={makeToggle(
          "airunner_show_art_prompt",
          !showArtPrompt,
          setShowArtPrompt,
        )}
        ttsOn={ttsOn}
        onToggleTts={makeToggle("airunner_tts_on", !ttsOn, setTtsOn)}
        sttOn={sttOn}
        onToggleStt={makeToggle("airunner_stt_on", !sttOn, setSttOn)}
        onOpenSettings={() => setShowSettings(true)}
        onSelectConversation={handleSelectConversation}
      >
        {showChat && <ChatView conversationId={conversationId} />}
      </Layout>

      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </>
  );
}
