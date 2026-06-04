import { useState, useEffect, useCallback, useRef } from "react";

const STORAGE_KEY = "airunner_active_downloads";

export interface DownloadJob {
  jobId: string;
  label: string;
  modelName?: string;
  baseModel?: string;
  modelType?: string;
  startedAt: string;
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

/**
 * Shared version counter incremented on every mutation.
 * All hook instances watch this counter via a custom DOM event.
 */
let _version = 0;
const EVENT = "airunner-dl-changed";

const COMPLETED_KEY = "airunner_completed_downloads";

function loadCompleted(): Set<string> {
  try {
    const raw = localStorage.getItem(COMPLETED_KEY);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function saveCompleted(urls: Set<string>) {
  try {
    localStorage.setItem(COMPLETED_KEY, JSON.stringify([...urls]));
  } catch { /* */ }
}

export function useDownloads() {
  const [ver, setVer] = useState(0);
  const downloads = useRef<DownloadJob[]>(load());

  useEffect(() => {
    const handler = () => {
      downloads.current = load();
      setVer((v) => v + 1);
    };
    window.addEventListener(EVENT, handler);
    return () => window.removeEventListener(EVENT, handler);
  }, []);

  const bump = useCallback(() => {
    _version++;
    downloads.current = load();
    setVer((v) => v + 1);
    try { window.dispatchEvent(new Event(EVENT)); } catch { /* */ }
  }, []);

  const addDownload = useCallback((job: DownloadJob) => {
    const next = [...load(), job];
    save(next);
    bump();
  }, [bump]);

  const removeDownload = useCallback((jobId: string) => {
    const next = load().filter((d) => d.jobId !== jobId);
    save(next);
    bump();
  }, [bump]);

  const clearDownloads = useCallback(() => {
    save([]);
    saveCompleted(new Set());
    bump();
  }, [bump]);

  const markCompleted = useCallback((downloadUrl: string) => {
    const set = loadCompleted();
    set.add(downloadUrl);
    saveCompleted(set);
    bump();
  }, [bump]);

  return {
    downloads: ver >= 0 ? downloads.current : downloads.current,
    addDownload,
    removeDownload,
    clearDownloads,
    markCompleted,
    isDownloaded: (url: string) => loadCompleted().has(url),
  };
}
