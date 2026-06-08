import { useLocalStorage } from "./useLocalStorage";

export type PanelId = "civitai_browser";

export function useLayoutPrefs() {
  const [showChat, setShowChat] = useLocalStorage("airunner_show_chat", true);
  const [showCanvas, setShowCanvas] = useLocalStorage("airunner_show_canvas", false);
  const [ttsOn, setTtsOn] = useLocalStorage("airunner_tts_on", false);
  const [sttOn, setSttOn] = useLocalStorage("airunner_stt_on", false);
  const [rawPanel, setRightPanel] = useLocalStorage<PanelId | null>("airunner_right_panel", null);
  // Sanitize stale "image_browser" value from before it moved into the canvas sidebar.
  const rightPanel: PanelId | null = rawPanel === "civitai_browser" ? "civitai_browser" : null;
  const [conversationId, setConversationId] = useLocalStorage<number | null>("airunner_conversation_id", null);

  return {
    showChat, setShowChat,
    showCanvas, setShowCanvas,
    ttsOn, setTtsOn,
    sttOn, setSttOn,
    rightPanel, setRightPanel,
    conversationId, setConversationId,
  };
}
