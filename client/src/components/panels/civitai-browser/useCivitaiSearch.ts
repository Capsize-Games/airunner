import { useState, useRef, useCallback, useEffect } from "react";
import { searchCivitaiModels } from "../../../api/downloads";
import { type JsonObject } from "../../../types/api";
import { useEventBus } from "../../../features/events/useEventBus";
import { EVENT_CIVITAI_THUMBNAIL } from "../../../features/events/types";
import { useCivitaiThumbnailCache } from "../../../hooks/useCivitaiThumbnailCache";
import { flattenItem, fetchFilterOptions, type SearchResult, type FilterOption } from "./civitaiUtils";

export function useCivitaiSearch(
  baseModel: string,
  modelType: string,
  selectedModelId: number | null,
  onThumbnailUpdate: (payload: {
    model_id?: number;
    thumbnails?: Record<string, string>;
  }) => void,
) {
  const thumbCache = useCivitaiThumbnailCache();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [filterOptions, setFilterOptions] = useState<{ baseModels: FilterOption[]; typesByBase: Record<string, string[]> }>({ baseModels: [], typesByBase: {} });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resultsElRef = useRef<HTMLDivElement | null>(null);
  const cursorRef = useRef<string | null>(null);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const fillCountRef = useRef(0);
  const doSearchRef = useRef<(append?: boolean) => void>(() => {});

  useEffect(() => {
    fetchFilterOptions()
      .then((opts) => setFilterOptions({ baseModels: opts.baseModels, typesByBase: opts.typesByBase }))
      .catch(() => {});
  }, []);

  useEventBus([EVENT_CIVITAI_THUMBNAIL], (_event, data) => {
    const payload = data as {
      model_id?: number;
      thumbnails?: Record<string, string>;
      model?: JsonObject;
      version_index?: number;
      image_url?: string;
      images_base64?: Record<string, string>;
    };

    if (
      payload.model_id === selectedModelId &&
      payload.version_index !== undefined &&
      payload.image_url &&
      payload.images_base64
    ) {
      thumbCache.store(payload.model_id!, payload.version_index, payload.image_url, payload.images_base64).catch(() => {});
      return;
    }

    if (!payload.model_id || !payload.thumbnails) return;
    onThumbnailUpdate({ model_id: payload.model_id, thumbnails: payload.thumbnails });
    setResults((prev) =>
      prev.map((r) =>
        r.id === payload.model_id
          ? { ...r, thumbnails: { ...r.thumbnails, ...payload.thumbnails } }
          : r,
      ),
    );
  });

  const shouldSearch = (): boolean => query.trim().length > 0 || (baseModel !== "" && modelType !== "");

  const doSearch = useCallback(async (append = false) => {
    if (!shouldSearch()) return;
    loadingRef.current = true;
    setLoading(true);
    try {
      const data = await searchCivitaiModels({
        query,
        base_models: baseModel ? [baseModel] : undefined,
        model_types: modelType ? [modelType] : undefined,
        limit: 20,
        cursor: append ? cursorRef.current : null,
      });
      const items = ((data.items ?? []) as JsonObject[]).map(flattenItem);
      setResults((prev) => (append ? [...prev, ...items] : items));
      const next = ((data.metadata as JsonObject | undefined)?.nextCursor as string) ?? null;
      cursorRef.current = next;
      hasMoreRef.current = next !== null;
      setHasMore(next !== null);
    } catch { /* network error */ } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, [query, baseModel, modelType]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { doSearchRef.current = doSearch; }, [doSearch]);

  const debouncedSearch = useCallback((append = false) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      cursorRef.current = null;
      hasMoreRef.current = true;
      doSearch(append);
    }, 400);
  }, [doSearch]);

  useEffect(() => {
    if (baseModel !== "" && modelType !== "") {
      doSearchRef.current?.(false);
    } else {
      setResults([]);
      cursorRef.current = null;
      hasMoreRef.current = true;
      setHasMore(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseModel, modelType]);

  useEffect(() => {
    if (selectedModelId !== null) { fillCountRef.current = 0; return; }
    if (!loading && hasMore && results.length > 0 && resultsElRef.current) {
      if (resultsElRef.current.scrollHeight <= resultsElRef.current.clientHeight && fillCountRef.current < 4) {
        fillCountRef.current++;
        doSearchRef.current?.(true);
      } else { fillCountRef.current = 0; }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results.length, loading, hasMore, selectedModelId]);

  const scrollMounted = useRef(false);
  const resultsRef = useCallback((el: HTMLDivElement | null) => {
    resultsElRef.current = el;
    if (el && !scrollMounted.current) {
      scrollMounted.current = true;
      const onScroll = () => {
        if (loadingRef.current || !hasMoreRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = el;
        if (scrollHeight - scrollTop - clientHeight < 150) doSearchRef.current?.(true);
      };
      el.addEventListener("scroll", onScroll, { passive: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleQueryChange = (val: string) => {
    setQuery(val);
    if (val.trim().length > 0) {
      debouncedSearch(false);
    } else if (baseModel !== "" && modelType !== "") {
      debouncedSearch(false);
    } else {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      setResults([]);
      cursorRef.current = null;
      hasMoreRef.current = true;
      setHasMore(true);
    }
  };

  return {
    query, results, loading, hasMore, filterOptions,
    shouldSearch, resultsRef,
    handleQueryChange,
  };
}
