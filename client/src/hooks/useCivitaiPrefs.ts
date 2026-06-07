import { useLocalStorage } from "./useLocalStorage";

export function useCivitaiPrefs() {
  const [baseModel, setBaseModel] = useLocalStorage("airunner_civitai_base_model", "");
  const [modelType, setModelType] = useLocalStorage("airunner_civitai_model_type", "");
  const [selectedModelId, setSelectedModelId] = useLocalStorage<number | null>("airunner_civitai_selected_model", null);
  const [apiKey, setApiKey] = useLocalStorage("airunner_civitai_api_key", "");

  return { baseModel, setBaseModel, modelType, setModelType, selectedModelId, setSelectedModelId, apiKey, setApiKey };
}
