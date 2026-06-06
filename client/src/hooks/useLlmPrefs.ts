import { useLocalStorage } from "./useLocalStorage";

export function useLlmPrefs() {
  const [modelPath, setModelPath] = useLocalStorage("airunner:modelPath", "");
  const [temperature, setTemperature] = useLocalStorage("airunner:temperature", 0.7);
  const [maxTokens, setMaxTokens] = useLocalStorage<number | null>("airunner:maxTokens", null);
  const [selectedVoice, setSelectedVoice] = useLocalStorage("airunner:selectedVoice", "");
  const [whisperModel, setWhisperModel] = useLocalStorage("airunner:whisperModel", "");
  const [activeTab, setActiveTab] = useLocalStorage("airunner:activeTab", "llm");

  return {
    modelPath, setModelPath,
    temperature, setTemperature,
    maxTokens, setMaxTokens,
    selectedVoice, setSelectedVoice,
    whisperModel, setWhisperModel,
    activeTab, setActiveTab,
  };
}
