export const LS_DATE_KEY = "airunner_image_browser_date";
export const LS_LOCAL_IMAGES_KEY = "airunner_local_images";

export interface LocalImageEntry {
  id: string;
  dataUrl: string;
  timestamp: string;
  prompt?: string;
  seed?: number;
  steps?: number;
  fileSize: number;
}

export function getLocalImages(): LocalImageEntry[] {
  try {
    const raw = localStorage.getItem(LS_LOCAL_IMAGES_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as LocalImageEntry[];
  } catch {
    return [];
  }
}

export function saveLocalImage(entry: LocalImageEntry): void {
  try {
    const existing = getLocalImages();
    existing.unshift(entry);
    const trimmed = existing.slice(0, 100);
    localStorage.setItem(LS_LOCAL_IMAGES_KEY, JSON.stringify(trimmed));
  } catch {
    // localStorage may be full
  }
}

export function deleteLocalImage(id: string): void {
  try {
    const existing = getLocalImages().filter((e) => e.id !== id);
    localStorage.setItem(LS_LOCAL_IMAGES_KEY, JSON.stringify(existing));
  } catch {
    // ignore
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function formatTimestamp(ts: number): string {
  try {
    const d = new Date(ts * 1000);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const mins = String(d.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${mins}`;
  } catch {
    return "";
  }
}

export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen) + "...";
}
