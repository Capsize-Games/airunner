import { useLocalStorage } from "./useLocalStorage";

export type PanelId =
  | "knowledge"
  | "history"
  | "llm_settings"
  | "lora"
  | "embeddings"
  | "image_browser"
  | "stats"
  | "civitai_browser";

export function useLayoutPrefs() {
  const [showChat, setShowChat] = useLocalStorage("airunner_show_chat", true);
  const [showCanvas, setShowCanvas] = useLocalStorage("airunner_show_canvas", false);
  const [ttsOn, setTtsOn] = useLocalStorage("airunner_tts_on", false);
  const [sttOn, setSttOn] = useLocalStorage("airunner_stt_on", false);
  const [leftPanel, setLeftPanel] = useLocalStorage<PanelId | null>("airunner_left_panel", null);
  const [rightPanel, setRightPanel] = useLocalStorage<PanelId | null>("airunner_right_panel", null);
  const [conversationId, setConversationId] = useLocalStorage<number | null>("airunner_conversation_id", null);

  return {
    showChat, setShowChat,
    showCanvas, setShowCanvas,
    ttsOn, setTtsOn,
    sttOn, setSttOn,
    leftPanel, setLeftPanel,
    rightPanel, setRightPanel,
    conversationId, setConversationId,
  };
}
