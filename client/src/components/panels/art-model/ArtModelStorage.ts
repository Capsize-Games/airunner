export const LS_KEY = "airunner_art_settings";

export function saveToStorage(key: string, val: number) {
  try {
    const data = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
    data[key] = val;
    localStorage.setItem(LS_KEY, JSON.stringify(data));
  } catch {
    /* */
  }
}

export function loadFromStorage(key: string, fallback: number): number {
  try {
    const data = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
    const v = data[key];
    return v !== undefined ? Number(v) : fallback;
  } catch {
    return fallback;
  }
}
