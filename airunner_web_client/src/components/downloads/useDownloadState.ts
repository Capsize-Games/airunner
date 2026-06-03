import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "airunner_active_downloads";
const CHANGE_EVENT = "airunner-downloads-changed";

export interface DownloadJob {
  jobId: string;
  label: string;
  modelName?: string;
  baseModel?: string;
  modelType?: string;
  startedAt: string;
  /** CivitAI download URL — preserved so Retry can re-submit. */
  downloadUrl?: string;
}

function load(): DownloadJob[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function save(jobs: DownloadJob[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  } catch { /* */ }
}

/** Shared module-level subscribers so all hook instances stay in sync. */
let _listeners: Array<() => void> = [];
function notify() { _listeners.forEach((fn) => fn()); }

export function useDownloads() {
  const [downloads, setDownloads] = useState<DownloadJob[]>(load);

  // Subscribe to cross-component change notifications
  useEffect(() => {
    const handler = () => setDownloads(load());
    _listeners.push(handler);
    return () => { _listeners = _listeners.filter((h) => h !== handler); };
  }, []);

  const addDownload = useCallback((job: DownloadJob) => {
    setDownloads((prev) => {
      const next = [...prev, job];
      save(next);
      notify();
      return next;
    });
  }, []);

  const removeDownload = useCallback((jobId: string) => {
    setDownloads((prev) => {
      const next = prev.filter((d) => d.jobId !== jobId);
      save(next);
      notify();
      return next;
    });
  }, []);

  const clearDownloads = useCallback(() => {
    setDownloads([]);
    save([]);
    notify();
  }, []);

  return { downloads, addDownload, removeDownload, clearDownloads };
}
