import { useCallback } from "react";

// ── useCivitaiThumbnailCache ──────────────────────────────────────────────────
// Server-only: always fetches thumbnails from the API.

export function useCivitaiThumbnailCache() {
  const store = useCallback(async (
    _modelId: number,
    _versionIndex: number,
    _imageUrl: string,
    _b64Map: Record<string, string>,
  ): Promise<void> => {
    // Thumbnails are fetched and cached server-side; no client cache.
  }, []);

  const getAll = useCallback(async (
    _modelId: number,
    _versionIndex: number,
  ): Promise<Record<string, Record<string, string>>> => {
    return {};
  }, []);

  return { store, getAll };
}
