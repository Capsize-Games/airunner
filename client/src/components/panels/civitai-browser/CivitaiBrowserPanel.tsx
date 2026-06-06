
import { useState, useRef, useCallback, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import CivitaiSearchBar from "./CivitaiSearchBar";
import CivitaiResultCard from "./CivitaiResultCard";
import { searchCivitaiModels, fetchCivitaiModel, requestCivitaiVersionThumbnails } from "../../../api/downloads";
import { request } from "../../../api/client-base";
import { BASE_URL, type JsonObject } from "../../../types/api";
import CivitaiModelDetailModal from "./CivitaiModelDetailModal";
import { useEventBus } from "../../../features/events/useEventBus";
import { EVENT_CIVITAI_THUMBNAIL } from "../../../features/events/types";

// Note: CivitAI data caching is handled server-side (72h for search
// results, permanent for images).  No client-side caching needed.

// ── Helpers ──

function thumbnailUrl(url: string, _width = 120): string { return url || ""; }

interface SearchResult {
  id: number; name: string; type?: string; baseModel?: string;
  creator?: string; thumbnail?: string;
  /** Inline base64 thumbnails from the server, keyed by size. */
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
  const [query, setQuery] = useState("");
  const [baseModel, setBaseModel] = useState(() => {
    try { return localStorage.getItem("airunner_civitai_base_model") ?? ""; }
    catch { return ""; }
  });
  const [modelType, setModelType] = useState(() => {
    try { return localStorage.getItem("airunner_civitai_model_type") ?? ""; }
    catch { return ""; }
  });
  const [results, setResults] = useState<SearchResult[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(() => {
    try {
      const v = localStorage.getItem("airunner_civitai_selected_model");
      return v ? Number(v) : null;
    } catch { return null; }
  });
  const [selectedModelData, setSelectedModelData] = useState<JsonObject | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filterOptions, setFilterOptions] = useState<{ baseModels: FilterOption[]; typesByBase: Record<string, string[]> }>({ baseModels: [], typesByBase: {} });

  const detailCache = useRef<Map<number, JsonObject>>(new Map());
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resultsElRef = useRef<HTMLDivElement | null>(null);
  const cursorRef = useRef<string | null>(null);
  const loadingRef = useRef(false);
  const hasMoreRef = useRef(true);
  const fillCountRef = useRef(0);
  const doSearchRef = useRef<(append?: boolean) => void>(() => {});

  // Load filter options on mount
  useEffect(() => { fetchFilterOptions().then((opts) => setFilterOptions({ baseModels: opts.baseModels, typesByBase: opts.typesByBase })).catch(() => {}); }, []);

  // Listen for streaming thumbnails pushed by the server
  useEventBus([EVENT_CIVITAI_THUMBNAIL], (_event, data) => {
    const payload = data as {
      model_id?: number;
      thumbnails?: Record<string, string>;
      model?: JsonObject;
      version_index?: number;
      image_url?: string;
      images_base64?: Record<string, string>;
    };
    // Per-image streaming update for version thumbnails
    if (
      payload.model_id === selectedModelId &&
      payload.version_index !== undefined &&
      payload.image_url &&
      payload.images_base64
    ) {
      const vIdx = payload.version_index;
      const imageUrl = payload.image_url;
      const b64 = payload.images_base64;
      setSelectedModelData((prev) => {
        if (!prev) return prev;
        const versions = [...((prev as JsonObject).modelVersions ?? [])] as JsonObject[];
        if (vIdx >= versions.length) return prev;
        const images = [...((versions[vIdx].images ?? []) as JsonObject[])];
        const iIdx = images.findIndex(
          (img) => (img.url ?? img.thumbnailUrl) === imageUrl,
        );
        if (iIdx < 0) return prev;
        images[iIdx] = { ...images[iIdx], images_base64: b64 };
        versions[vIdx] = { ...versions[vIdx], images };
        return { ...(prev as JsonObject), modelVersions: versions };
      });
      return;
    }
    // Full model update (legacy fallback)
    if (payload.model && payload.model_id === selectedModelId) {
      setSelectedModelData(payload.model);
      return;
    }
    // Search result thumbnail update
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
    const pageLabel = append ? `page-2 (cursor=${cursorRef.current?.slice(0, 20)}...)` : "page-1";
    console.log(`[CivitAI] doSearch ${pageLabel} — sending POST`);
    try {
      const data = await searchCivitaiModels({
        query,
        base_models: baseModel ? [baseModel] : undefined,
        model_types: modelType ? [modelType] : undefined,
        limit: 20,
        cursor: append ? cursorRef.current : null,
      });
      console.log(`[CivitAI] doSearch ${pageLabel} — got response, items=${(data.items as unknown[])?.length}`);
      const items = ((data.items ?? []) as JsonObject[]).map(flattenItem);
      setResults((prev) => (append ? [...prev, ...items] : items));
      const next = ((data.metadata as JsonObject | undefined)?.nextCursor as string) ?? null;
      cursorRef.current = next;
      hasMoreRef.current = next !== null;
      setCursor(next);
      setHasMore(next !== null);
    } catch (err) {
      console.error(`[CivitAI] doSearch ${pageLabel} — FAILED:`, err);
    }
    finally { setLoading(false); loadingRef.current = false; }
  }, [query, baseModel, modelType]);

  // Keep ref in sync so event handlers never capture stale closures
  useEffect(() => { doSearchRef.current = doSearch; }, [doSearch]);

  const debouncedSearch = useCallback((append = false) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { cursorRef.current = null; hasMoreRef.current = true; doSearch(append); }, 400);
  }, [doSearch]);

  // Auto-search on dropdown change — fire immediately on mount when
  // filters are restored from localStorage (no debounce).
  useEffect(() => {
    if (baseModel !== "" && modelType !== "") {
      if (doSearchRef.current) {
        doSearchRef.current(false);
      }
    } else {
      setResults([]);
      cursorRef.current = null;
      hasMoreRef.current = true;
      setHasMore(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseModel, modelType]);

  // Viewport filling — skip when modal is open
  useEffect(() => {
    if (selectedModelId !== null) { fillCountRef.current = 0; return; }
    if (!loading && hasMore && results.length > 0 && resultsElRef.current) {
      if (resultsElRef.current.scrollHeight <= resultsElRef.current.clientHeight && fillCountRef.current < 4) {
        fillCountRef.current++;
        doSearchRef.current(true);
      } else { fillCountRef.current = 0; }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results.length, loading, hasMore, selectedModelId]);

  // Scroll lazy loading — attached via callback ref so it's always active
  const scrollMounted = useRef(false);
  const resultsRef = useCallback((el: HTMLDivElement | null) => {
    resultsElRef.current = el;
    if (el && !scrollMounted.current) {
      scrollMounted.current = true;
      const onScroll = () => {
        if (loadingRef.current || !hasMoreRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = el;
        if (scrollHeight - scrollTop - clientHeight < 150) {
          doSearchRef.current(true);
        }
      };
      el.addEventListener("scroll", onScroll, { passive: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectModel = useCallback(async (modelId: number) => {
    setSelectedModelId(modelId);
    try { localStorage.setItem("airunner_civitai_selected_model", String(modelId)); } catch { /* */ }
    const cached = detailCache.current.get(modelId);
    if (cached) { setSelectedModelData(cached); return; }
    setSelectedModelData({ id: modelId, name: "Loading...", modelVersions: [] } as unknown as JsonObject);
    setDetailLoading(true);
    try {
      const data = await fetchCivitaiModel({
        model_id: String(modelId),
        base_models: baseModel ? [baseModel] : undefined,
        model_types: modelType ? [modelType] : undefined,
      });
      detailCache.current.set(modelId, data);
      setSelectedModelData(data);
    } catch {
      setSelectedModelData(null);
    } finally {
      setDetailLoading(false);
    }
  }, [baseModel, modelType]);

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

  // Re-fetch model detail on mount when restoring from localStorage
  useEffect(() => {
    const storedId = selectedModelId;
    if (storedId === null) return;
    if (detailCache.current.has(storedId)) {
      setSelectedModelData(detailCache.current.get(storedId) ?? null);
      return;
    }
    if (baseModel === "" || modelType === "") return; // wait for filters
    setDetailLoading(true);
    fetchCivitaiModel({
      model_id: String(storedId),
      base_models: baseModel ? [baseModel] : undefined,
      model_types: modelType ? [modelType] : undefined,
    }).then((data) => {
      detailCache.current.set(storedId, data);
      setSelectedModelData(data);
    }).catch(() => {}).finally(() => setDetailLoading(false));
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
        onQueryChange={(val) => { setQuery(val); if (val.trim().length > 0) debouncedSearch(false); }}
        onBaseModelChange={(val) => {
          setBaseModel(val);
          setModelType("");
          try { localStorage.setItem("airunner_civitai_base_model", val); } catch { /* */ }
          try { localStorage.setItem("airunner_civitai_model_type", ""); } catch { /* */ }
        }}
        onModelTypeChange={(val) => {
          setModelType(val);
          try { localStorage.setItem("airunner_civitai_model_type", val); } catch { /* */ }
        }}
      />

      <div ref={resultsRef} className="overflow-auto" style={{ flex: 1, minHeight: 0 }}>
        {results.map((item) => (
          <CivitaiResultCard key={item.id} item={item} selected={selectedModelId === item.id} onSelect={handleSelectModel} />
        ))}
        {loading && <div className="text-center py-2"><Spinner animation="border" size="sm" /></div>}
        {!loading && results.length === 0 && (
          <p className="text-muted small text-center mt-3">
            {shouldSearch() ? "No results found." : "Select a base model and type, or type a search query."}
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
            try { localStorage.removeItem("airunner_civitai_selected_model"); } catch { /* */ }
          }}
        />
      )}
    </div>
  );
}
