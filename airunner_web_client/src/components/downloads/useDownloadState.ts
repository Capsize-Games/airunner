import { useState, useCallback } from "react";

const STORAGE_KEY = "airunner_active_downloads";

export interface DownloadJob {
  jobId: string;
  label: string;
  modelName?: string;
  baseModel?: string;
  modelType?: string;
  startedAt: string;
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

export function useDownloads() {
  const [downloads, setDownloads] = useState<DownloadJob[]>(load);

  const addDownload = useCallback((job: DownloadJob) => {
    setDownloads((prev) => {
      const next = [...prev, job];
      save(next);
      return next;
    });
  }, []);

  const removeDownload = useCallback((jobId: string) => {
    setDownloads((prev) => {
      const next = prev.filter((d) => d.jobId !== jobId);
      save(next);
      return next;
    });
  }, []);

  const clearDownloads = useCallback(() => {
    setDownloads([]);
    save([]);
  }, []);

  return { downloads, addDownload, removeDownload, clearDownloads };
}
