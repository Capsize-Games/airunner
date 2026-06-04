export const STORAGE_KEY = "airunner_art_prompt_data";

export interface PromptData {
  prompt: string;
  negative_prompt: string;
  secondary_prompt: string;
  secondary_negative_prompt: string;
}

export const DEFAULT_PROMPT_DATA: PromptData = {
  prompt: "",
  negative_prompt: "",
  secondary_prompt: "",
  secondary_negative_prompt: "",
};

export function loadPromptData(): PromptData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as PromptData;
  } catch {
    /* ignore */
  }
  return { ...DEFAULT_PROMPT_DATA };
}

export function savePromptData(data: Record<string, string>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    /* ignore */
  }
}
