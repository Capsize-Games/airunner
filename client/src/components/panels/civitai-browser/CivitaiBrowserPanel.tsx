import { useState, useRef, useCallback, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import CivitaiSearchBar from "./CivitaiSearchBar";
import CivitaiResultCard from "./CivitaiResultCard";
import { searchCivitaiModels, fetchCivitaiModel, requestCivitaiVersionThumbnails } from "../../../api/downloads";
import { request } from "../../../api/client-base";
import { type JsonObject } from "../../../types/api";
import CivitaiModelDetailModal from "./CivitaiModelDetailModal";
import { useEventBus } from "../../../features/events/useEventBus";
import { EVENT_CIVITAI_THUMBNAIL } from "../../../features/events/types";
import { useCivitaiPrefs } from "../../../hooks/useCivitaiPrefs";
import { useCivitaiDetailCache } from "../../../hooks/useCivitaiDetailCache";
import { useCivitaiThumbnailCache } from "../../../hooks/useCivitaiThumbnailCache";

// ── Helpers ──

interface SearchResult {
  id: number; name: string; type?: string; baseModel?: string;
  creator?: string; thumbnail?: string;
  thumbnails?: Record<string, string>;
}

function flattenItem(item: JsonObject): SearchResult {
  const creatorObj = item.creator as JsonObject | undefined;
  const creatorName = creatorObj?.username ? String(creatorObj.username) : String(item.creator ?? "Unknown");
  const versions = (item.modelVersions ?? []) as JsonObject[];
  let thumbUrl = "";
  if (versions.length > 0) {
    const images = (versions[0].images ?? []) as JsonObject[];
    if (images.length > 0) thumbUrl = String(images[0].url ?? images[0].thumbnailUrl ?? "");
  }
  if (!thumbUrl) thumbUrl = String((item as JsonObject).image ?? "");
  return {
    id: Number(item.id), name: String(item.name ?? ""),
    type: item.type ? String(item.type) : undefined,
    baseModel: item.baseModel ? String(item.baseModel) : undefined,
    creator: creatorName,
    thumbnail: thumbUrl || undefined,
    thumbnails: (item.thumbnails as Record<string, string> | undefined) || undefined,
  };
}

// ── Filters from API ──

interface FilterOption { label: string; value: string; }

async function fetchFilterOptions(): Promise<{ baseModels: FilterOption[]; modelTypes: string[]; typesByBase: Record<string, string[]> }> {
  const data = await request<{ base_models: FilterOption[]; model_types: string[]; model_types_by_base: Record<string, string[]> }>(
    "GET", "/api/v1/downloads/civitai/options",
  );
  return { baseModels: data.base_models ?? [], modelTypes: data.model_types ?? [], typesByBase: data.model_types_by_base ?? {} };
}

// ── Panel component ──

export default function CivitaiBrowserPanel() {
  const {
    baseModel, setBaseModel,
    modelType, setModelType,
    selectedModelId, setSelectedModelId,
  } = useCivitaiPrefs();

  const detailCache = useCivitaiDetailCache();
  const thumbCache = useCivitaiThumbnailCache();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [selectedModelData, setSelectedModelData] = useState<JsonObject | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
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

  // Listen for streaming thumbnails pushed by the server; persist to IndexedDB.
  useEventBus([EVENT_CIVITAI_THUMBNAIL], (_event, data) => {
    const payload = data as {
      model_id?: number;
      thumbnails?: Record<string, string>;
      model?: JsonObject;
      version_index?: number;
      image_url?: string;
      images_base64?: Record<string, string>;
    };

    // Per-image streaming update for version thumbnails.
    if (
      payload.model_id === selectedModelId &&
      payload.version_index !== undefined &&
      payload.image_url &&
      payload.images_base64
    ) {
      const vIdx = payload.version_index;
      const imageUrl = payload.image_url;
      const b64Map = payload.images_base64;

      // Persist each size variant to IndexedDB.
      for (const [, blob] of Object.entries(b64Map)) {
        thumbCache.store(payload.model_id!, vIdx, imageUrl, blob).catch(() => {});
      }

      setSelectedModelData((prev) => {
        if (!prev) return prev;
        const versions = [...((prev as JsonObject).modelVersions ?? [])] as JsonObject[];
        if (vIdx >= versions.length) return prev;
        const images = [...((versions[vIdx].images ?? []) as JsonObject[])];
        const iIdx = images.findIndex(
          (img) => (img.url ?? img.thumbnailUrl) === imageUrl,
        );
        if (iIdx < 0) return prev;
        images[iIdx] = { ...images[iIdx], images_base64: b64Map };
        versions[vIdx] = { ...versions[vIdx], images };
        return { ...(prev as JsonObject), modelVersions: versions };
      });
      return;
    }

    // Full model update (legacy fallback).
    if (payload.model && payload.model_id === selectedModelId) {
      setSelectedModelData(payload.model);
      return;
    }

    // Search result thumbnail update.
    if (!payload.model_id || !payload.thumbnails) return;
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
      setCursor(next);
      setHasMore(next !== null);
    } catch { /* network error */ } finally {
      setLoading(false);
      loadingRef.current = false;
    }
  }, [query, baseModel, modelType]);

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

  // Viewport fill.
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

  // Scroll lazy loading.
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

  const fetchModelDetail = useCallback(async (modelId: number) => {
    // Check IndexedDB cache first.
    const cached = await detailCache.get(modelId);
    if (cached) { setSelectedModelData(cached); setDetailLoading(false); return; }

    setSelectedModelData({ id: modelId, name: "Loading...", modelVersions: [] } as unknown as JsonObject);
    setDetailLoading(true);
    try {
      const data = await fetchCivitaiModel({
        model_id: String(modelId),
        base_models: baseModel ? [baseModel] : undefined,
        model_types: modelType ? [modelType] : undefined,
      });
      await detailCache.set(modelId, data);
      setSelectedModelData(data);
    } catch {
      setSelectedModelData(null);
    } finally {
      setDetailLoading(false);
    }
  }, [baseModel, modelType, detailCache]);

  const handleSelectModel = useCallback(async (modelId: number) => {
    setSelectedModelId(modelId);
    await fetchModelDetail(modelId);
  }, [fetchModelDetail, setSelectedModelId]);

  const handleRequestVersionThumbnails = useCallback(async (versionId: number) => {
    if (!selectedModelData) return;
    const versions = ((selectedModelData as JsonObject).modelVersions ?? []) as JsonObject[];
    const versionIndex = versions.findIndex((v) => Number(v.id) === versionId);
    if (versionIndex < 0) return;
    try {
      await requestCivitaiVersionThumbnails({
        model_data: selectedModelData,
        version_index: versionIndex,
      });
    } catch { /* */ }
  }, [selectedModelData]);

  // Restore selected model detail on mount if filters are already set.
  useEffect(() => {
    if (selectedModelId === null) return;
    if (baseModel === "" || modelType === "") return;
    fetchModelDetail(selectedModelId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseModel, modelType]);

  const modelDetail = selectedModelData
    ? (() => {
        const raw = selectedModelData as JsonObject;
        const creatorObj = raw.creator as JsonObject | undefined;
        const creatorName = creatorObj?.username ? String(creatorObj.username) : String(raw.creator ?? "Unknown");
        const versions = (raw.modelVersions ?? []) as JsonObject[];
        return {
          id: Number(raw.id ?? 0), name: String(raw.name ?? ""),
          description: raw.description ? String(raw.description) : undefined,
          creator: creatorName, type: raw.type ? String(raw.type) : undefined,
          stats: raw.stats as { downloadCount?: number; favoriteCount?: number; commentCount?: number } | undefined,
          allowNoCredit: raw.allowNoCredit === true,
          allowCommercialUse: raw.allowCommercialUse === true ? "Commercial" : (raw.allowCommercialUse === false ? "Non-Commercial" : undefined),
          allowDerivatives: raw.allowDerivatives === true ? "Allowed" : (raw.allowDerivatives === false ? "Not allowed" : undefined),
          allowDifferentLicense: raw.allowDifferentLicense === true,
          versions: versions.map((v: JsonObject) => ({
            id: Number(v.id), name: String(v.name ?? ""),
            baseModel: v.baseModel ? String(v.baseModel) : undefined,
            files: ((v.files ?? []) as JsonObject[]).map((f: JsonObject) => ({
              id: Number(f.id), name: String(f.name ?? ""),
              sizeKB: f.sizeKB ? Number(f.sizeKB) : undefined,
              downloadUrl: f.downloadUrl ? String(f.downloadUrl) : undefined,
              downloaded: f.downloaded === true,
            })),
            images: ((v.images ?? []) as JsonObject[]).map((img: JsonObject) => ({
              url: String(img.url ?? img.thumbnailUrl ?? ""),
              nsfw: img.nsfw ? String(img.nsfw) : undefined,
              width: img.width ? Number(img.width) : undefined,
              height: img.height ? Number(img.height) : undefined,
              images_base64: (img.images_base64 as Record<string, string> | undefined) || undefined,
            })),
          })),
        };
      })()
    : null;

  return (
    <div className="d-flex flex-column h-100 p-2" style={{ position: "relative" }}>
      <h6 className="text-muted mb-2">CivitAI Browser</h6>

      <CivitaiSearchBar
        query={query} baseModel={baseModel} modelType={modelType}
        filterOptions={filterOptions}
        onQueryChange={(val) => {
          setQuery(val);
          if (val.trim().length > 0) debouncedSearch(false);
        }}
        onBaseModelChange={(val) => {
          setBaseModel(val);
          setModelType("");
        }}
        onModelTypeChange={setModelType}
      />

      <div ref={resultsRef} className="overflow-auto" style={{ flex: 1, minHeight: 0 }}>
        {results.map((item) => (
          <CivitaiResultCard
            key={item.id}
            item={item}
            selected={selectedModelId === item.id}
            onSelect={handleSelectModel}
          />
        ))}
        {loading && (
          <div className="text-center py-2">
            <Spinner animation="border" size="sm" />
          </div>
        )}
        {!loading && results.length === 0 && (
          <p className="text-muted small text-center mt-3">
            {shouldSearch()
              ? "No results found."
              : "Select a base model and type, or type a search query."}
          </p>
        )}
      </div>

      {selectedModelId !== null && (
        <CivitaiModelDetailModal
          model={modelDetail}
          loading={detailLoading}
          baseModel={baseModel}
          modelType={modelType}
          onVersionChange={handleRequestVersionThumbnails}
          onClose={() => {
            setSelectedModelId(null);
            setSelectedModelData(null);
          }}
        />
      )}
    </div>
  );
}
