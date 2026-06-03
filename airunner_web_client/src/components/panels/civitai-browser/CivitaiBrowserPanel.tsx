
import { useState, useRef, useCallback, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import CivitaiSearchBar from "./CivitaiSearchBar";
import CivitaiResultCard from "./CivitaiResultCard";
import { searchCivitaiModels, fetchCivitaiModel } from "../../../api/downloads";
import { BASE_URL, type JsonObject } from "../../../types/api";
import CivitaiModelDetailModal from "./CivitaiModelDetailModal";

// ── Cache helpers (localStorage, 24-hour TTL) ──

const CACHE_KEY_PREFIX = "airunner_civitai_cache_";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

interface CacheEntry<T> { data: T; ts: number; }

function cacheGet<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY_PREFIX + key);
    if (!raw) return null;
    const entry = JSON.parse(raw) as CacheEntry<T>;
    if (Date.now() - entry.ts > CACHE_TTL_MS) {
      localStorage.removeItem(CACHE_KEY_PREFIX + key);
      return null;
    }
    return entry.data;
  } catch { return null; }
}

function cacheSet<T>(key: string, data: T) {
  try {
    localStorage.setItem(CACHE_KEY_PREFIX + key, JSON.stringify({ data, ts: Date.now() } as CacheEntry<T>));
  } catch { /* */ }
}

let toastTimeout: ReturnType<typeof setTimeout> | null = null;

function clearAllCache(setToastMsg: (msg: string | null) => void) {
  const keys: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k && k.startsWith(CACHE_KEY_PREFIX)) keys.push(k);
  }
  keys.forEach((k) => localStorage.removeItem(k));
  setToastMsg(`Cache cleared (${keys.length} entries)`);
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => setToastMsg(null), 2000);
}

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
  const cacheKey = "filter_options";
  const cached = cacheGet<{ baseModels: FilterOption[]; modelTypes: string[]; typesByBase: Record<string, string[]> }>(cacheKey);
  if (cached) return cached;
  const res = await fetch(`${BASE_URL}/api/v1/downloads/civitai/options`);
  const data = await res.json() as { base_models: FilterOption[]; model_types: string[]; model_types_by_base: Record<string, string[]> };
  const result = { baseModels: data.base_models ?? [], modelTypes: data.model_types ?? [], typesByBase: data.model_types_by_base ?? {} };
  cacheSet(cacheKey, result);
  return result;
}

// ── Panel component ──

export default function CivitaiBrowserPanel() {
  const [query, setQuery] = useState("");
  const [baseModel, setBaseModel] = useState("");
  const [modelType, setModelType] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [selectedModelData, setSelectedModelData] = useState<JsonObject | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [filterOptions, setFilterOptions] = useState<{ baseModels: FilterOption[]; typesByBase: Record<string, string[]> }>({ baseModels: [], typesByBase: {} });
  const [toastMsg, setToastMsg] = useState<string | null>(null);

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

  // Auto-search on dropdown change
  useEffect(() => {
    if (baseModel !== "" && modelType !== "") { debouncedSearch(false); }
    else { setResults([]); cursorRef.current = null; hasMoreRef.current = true; setHasMore(true); }
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseModel, modelType]);

  // Viewport filling
  useEffect(() => {
    if (!loading && hasMore && results.length > 0 && resultsElRef.current) {
      if (resultsElRef.current.scrollHeight <= resultsElRef.current.clientHeight && fillCountRef.current < 4) {
        fillCountRef.current++;
        doSearchRef.current(true);
      } else { fillCountRef.current = 0; }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results.length, loading, hasMore]);

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
    const cached = detailCache.current.get(modelId);
    if (cached) { setSelectedModelData(cached); return; }
    // Show modal skeleton immediately with a placeholder
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
    } catch { /* */ }
    finally { setDetailLoading(false); }
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
          versions: versions.map((v: JsonObject) => ({
            id: Number(v.id), name: String(v.name ?? ""),
            baseModel: v.baseModel ? String(v.baseModel) : undefined,
            files: ((v.files ?? []) as JsonObject[]).map((f: JsonObject) => ({
              id: Number(f.id), name: String(f.name ?? ""),
              sizeKB: f.sizeKB ? Number(f.sizeKB) : undefined,
              downloadUrl: f.downloadUrl ? String(f.downloadUrl) : undefined,
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

  const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

  return (
    <div className="d-flex flex-column h-100 p-2" style={{ position: "relative" }}>
      <div className="d-flex align-items-center justify-content-between mb-2">
        <h6 className="text-muted mb-0">CivitAI Browser</h6>
        <button
          onClick={() => clearAllCache(setToastMsg)}
          style={{ background: "transparent", border: "none", cursor: "pointer", padding: 0, fontSize: 12, color: "#888" }}
          title="Clear API cache"
        >
          <img src={icon("delete")} alt="Clear cache" style={{ width: 14, height: 14, filter: "invert(0.5)" }} />
        </button>
      </div>

      {toastMsg && (
        <div style={{ position: "absolute", top: 30, right: 8, zIndex: 10, background: "var(--theme-bg-secondary)", border: "1px solid var(--bs-primary)", borderRadius: 4, padding: "2px 8px", fontSize: 10, color: "var(--bs-body-color)", whiteSpace: "nowrap", pointerEvents: "none" }}>
          {toastMsg}
        </div>
      )}

      <CivitaiSearchBar
        query={query} baseModel={baseModel} modelType={modelType}
        filterOptions={filterOptions}
        onQueryChange={(val) => { setQuery(val); if (val.trim().length > 0) debouncedSearch(false); }}
        onBaseModelChange={(val) => { setBaseModel(val); setModelType(""); }}
        onModelTypeChange={(val) => { setModelType(val); }}
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
          onClose={() => { setSelectedModelId(null); setSelectedModelData(null); }}
        />
      )}
    </div>
  );
}
