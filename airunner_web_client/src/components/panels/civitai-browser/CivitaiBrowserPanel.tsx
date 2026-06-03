import { useState, useRef, useCallback, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import CivitaiSearchBar from "./CivitaiSearchBar";
import CivitaiResultCard from "./CivitaiResultCard";
import CivitaiModelDetail from "./CivitaiModelDetail";
import DownloadProgress from "../../downloads/DownloadProgress";
import {
  searchCivitaiModels,
  fetchCivitaiModel,
  startCivitaiFileDownload,
} from "../../../api/downloads";
import { BASE_URL, type JsonObject } from "../../../types/api";

// ── Cache helpers (localStorage, 24-hour TTL) ──

const CACHE_KEY_PREFIX = "airunner_civitai_cache_";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

interface CacheEntry<T> {
  data: T;
  ts: number;
}

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
  } catch {
    return null;
  }
}

function cacheSet<T>(key: string, data: T) {
  try {
    localStorage.setItem(
      CACHE_KEY_PREFIX + key,
      JSON.stringify({ data, ts: Date.now() } as CacheEntry<T>),
    );
  } catch {
    // storage full — ignore
  }
}

let toastTimeout: ReturnType<typeof setTimeout> | null = null;

function clearAllCache(
  setToastMsg: (msg: string | null) => void,
) {
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

// Pass the CivitAI URL as-is to the proxy. The proxy enforces max_bytes
// to cap the response size server-side.
function thumbnailUrl(url: string, _width = 120): string {
  return url || "";
}

// ── Search result flattening ──

interface SearchResult {
  id: number;
  name: string;
  type?: string;
  baseModel?: string;
  creator?: string;
  thumbnail?: string;
}

function flattenItem(item: JsonObject): SearchResult {
  const creatorObj = item.creator as JsonObject | undefined;
  const creatorName = creatorObj?.username
    ? String(creatorObj.username)
    : String(item.creator ?? "Unknown");

  const versions = (item.modelVersions ?? []) as JsonObject[];
  let thumbUrl = "";
  if (versions.length > 0) {
    const images = (versions[0].images ?? []) as JsonObject[];
    if (images.length > 0) {
      thumbUrl = String(
        images[0].url ?? images[0].thumbnailUrl ?? "",
      );
    }
  }
  if (!thumbUrl) {
    thumbUrl = String((item as JsonObject).image ?? "");
  }

  return {
    id: Number(item.id),
    name: String(item.name ?? ""),
    type: item.type ? String(item.type) : undefined,
    baseModel: item.baseModel ? String(item.baseModel) : undefined,
    creator: creatorName,
    thumbnail: thumbUrl ? thumbnailUrl(thumbUrl) : undefined,
  };
}

// ── Filters from API ──

interface FilterOption {
  label: string;
  value: string;
}

async function fetchFilterOptions(): Promise<{
  baseModels: FilterOption[];
  modelTypes: string[];
  typesByBase: Record<string, string[]>;
}> {
  const cacheKey = "filter_options";
  const cached = cacheGet<{
    baseModels: FilterOption[];
    modelTypes: string[];
    typesByBase: Record<string, string[]>;
  }>(cacheKey);
  if (cached) return cached;

  const res = await fetch(
    `${BASE_URL}/api/v1/downloads/civitai/options`,
  );
  const data = (await res.json()) as {
    base_models: FilterOption[];
    model_types: string[];
    model_types_by_base: Record<string, string[]>;
  };

  const result = {
    baseModels: data.base_models ?? [],
    modelTypes: data.model_types ?? [],
    typesByBase: data.model_types_by_base ?? {},
  };
  cacheSet(cacheKey, result);
  return result;
}

// ── Panel component ──

interface DownloadJob {
  jobId: string;
  label: string;
}

export default function CivitaiBrowserPanel() {
  const [query, setQuery] = useState("");
  const [baseModel, setBaseModel] = useState("");
  const [modelType, setModelType] = useState("");

  const [results, setResults] = useState<SearchResult[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  const [selectedModelId, setSelectedModelId] = useState<number | null>(
    null,
  );
  const [selectedModelData, setSelectedModelData] =
    useState<JsonObject | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [downloads, setDownloads] = useState<DownloadJob[]>([]);

  const [filterOptions, setFilterOptions] = useState<{
    baseModels: FilterOption[];
    typesByBase: Record<string, string[]>;
  }>({ baseModels: [], typesByBase: {} });

  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const detailCache = useRef<Map<number, JsonObject>>(new Map());
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  // Load filter options on mount
  useEffect(() => {
    fetchFilterOptions()
      .then((opts) =>
        setFilterOptions({
          baseModels: opts.baseModels,
          typesByBase: opts.typesByBase,
        }),
      )
      .catch(() => {});
  }, []);

  // Only search when user has selected both dropdowns OR entered text
  const shouldSearch = useCallback((): boolean => {
    return (
      query.trim().length > 0 ||
      (baseModel !== "" && modelType !== "")
    );
  }, [query, baseModel, modelType]);

  const performSearch = useCallback(
    async (append = false) => {
      if (!shouldSearch()) return;
      setLoading(true);
      try {
        const baseModels = baseModel ? [baseModel] : undefined;
        const modelTypes = modelType ? [modelType] : undefined;
        const data = await searchCivitaiModels({
          query,
          base_models: baseModels,
          model_types: modelTypes,
          limit: 20,
          cursor: append ? cursor : null,
        });
        const items: SearchResult[] = (
          (data.items ?? []) as JsonObject[]
        ).map(flattenItem);
        if (append) {
          setResults((prev) => [...prev, ...items]);
        } else {
          setResults(items);
        }
        const meta = data.metadata as JsonObject | undefined;
        const next = (meta?.nextCursor as string) ?? null;
        setCursor(next);
        setHasMore(next !== null);
      } catch {
        // search failed
      } finally {
        setLoading(false);
      }
    },
    [query, baseModel, modelType, cursor, shouldSearch],
  );

  const debouncedSearch = useCallback(
    (append = false) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        setCursor(null);
        performSearch(append);
      }, 400);
    },
    [performSearch],
  );

  // Auto-search when dropdowns change (only if both selected)
  useEffect(() => {
    if (baseModel !== "" && modelType !== "") {
      debouncedSearch(false);
    } else {
      // Clear results when selections are incomplete
      setResults([]);
      setCursor(null);
      setHasMore(true);
    }
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseModel, modelType]);

  // IntersectionObserver lazy loading
  useEffect(() => {
    if (!sentinelRef.current) return;
    if (observerRef.current) observerRef.current.disconnect();
    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          performSearch(true);
        }
      },
      { rootMargin: "200px" },
    );
    observerRef.current.observe(sentinelRef.current);
    return () => {
      if (observerRef.current) observerRef.current.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMore, loading, cursor, query, baseModel, modelType]);

  const resultsRef = useRef<HTMLDivElement | null>(null);

  const handleSelectModel = useCallback(
    async (modelId: number) => {
      setSelectedModelId(modelId);

      // Scroll the selected card to the top of the results list
      if (resultsRef.current) {
        const el = resultsRef.current.querySelector(
          `[data-model-id="${modelId}"]`,
        ) as HTMLElement | null;
        if (el) {
          el.scrollIntoView({ block: "start", behavior: "smooth" });
        }
      }

      const cached = detailCache.current.get(modelId);
      if (cached) {
        setSelectedModelData(cached);
        return;
      }
      setDetailLoading(true);
      setSelectedModelData(null);
      try {
        const baseModels = baseModel ? [baseModel] : undefined;
        const modelTypes = modelType ? [modelType] : undefined;
        const data = await fetchCivitaiModel({
          model_id: String(modelId),
          base_models: baseModels,
          model_types: modelTypes,
        });
        detailCache.current.set(modelId, data);
        setSelectedModelData(data);
      } catch {
        // failed
      } finally {
        setDetailLoading(false);
      }
    },
    [baseModel, modelType],
  );

  const handleDownload = async (
    fileUrl: string,
    fileName: string,
  ) => {
    try {
      const basePath = "/tmp/airunner/downloads";
      const result = await startCivitaiFileDownload({
        url: fileUrl,
        output_path: `${basePath}/${fileName}`,
      });
      if (result.job_id) {
        setDownloads((prev) => [
          ...prev,
          { jobId: result.job_id, label: fileName },
        ]);
      }
    } catch {
      // download failed
    }
  };

  // Transform API data for detail component
  const modelDetail = selectedModelData
    ? (() => {
        const raw = selectedModelData as JsonObject;
        const creatorObj = raw.creator as JsonObject | undefined;
        const creatorName = creatorObj?.username
          ? String(creatorObj.username)
          : String(raw.creator ?? "Unknown");
        const versions = (raw.modelVersions ?? []) as JsonObject[];
        return {
          id: Number(raw.id ?? 0),
          name: String(raw.name ?? ""),
          description: raw.description
            ? String(raw.description)
            : undefined,
          creator: creatorName,
          type: raw.type ? String(raw.type) : undefined,
          stats: raw.stats as
            | {
                downloadCount?: number;
                favoriteCount?: number;
                commentCount?: number;
              }
            | undefined,
          versions: versions.map((v: JsonObject) => ({
            id: Number(v.id),
            name: String(v.name ?? ""),
            baseModel: v.baseModel ? String(v.baseModel) : undefined,
            files: ((v.files ?? []) as JsonObject[]).map(
              (f: JsonObject) => ({
                id: Number(f.id),
                name: String(f.name ?? ""),
                sizeKB: f.sizeKB ? Number(f.sizeKB) : undefined,
                downloadUrl: f.downloadUrl
                  ? String(f.downloadUrl)
                  : undefined,
              }),
            ),
            images: ((v.images ?? []) as JsonObject[]).map(
              (img: JsonObject) => ({
                url: String(
                  img.url ?? img.thumbnailUrl ?? "",
                ),
                nsfw: img.nsfw ? String(img.nsfw) : undefined,
                width: img.width ? Number(img.width) : undefined,
                height: img.height ? Number(img.height) : undefined,
              }),
            ),
          })),
        };
      })()
    : null;

  const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

  return (
    <div className="d-flex flex-column h-100 p-2">
      <div className="d-flex align-items-center justify-content-between mb-2">
        <h6 className="text-muted mb-0">CivitAI Browser</h6>
        <button
          onClick={() => clearAllCache(setToastMsg)}
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: 0,
            fontSize: 12,
            color: "#888",
          }}
          title="Clear API cache"
        >
          <img
            src={icon("delete")}
            alt="Clear cache"
            style={{
              width: 14,
              height: 14,
              filter: "invert(0.5)",
            }}
          />
        </button>
      </div>

      {/* Toast next to clear button */}
      {toastMsg && (
        <div
          style={{
            position: "absolute",
            top: 30,
            right: 8,
            zIndex: 10,
            background: "var(--theme-bg-secondary)",
            border: "1px solid var(--bs-primary)",
            borderRadius: 4,
            padding: "2px 8px",
            fontSize: 10,
            color: "var(--bs-body-color)",
            whiteSpace: "nowrap",
            pointerEvents: "none",
          }}
        >
          {toastMsg}
        </div>
      )}

      {/* Search */}
      <CivitaiSearchBar
        query={query}
        baseModel={baseModel}
        modelType={modelType}
        filterOptions={filterOptions}
        onQueryChange={(val) => {
          setQuery(val);
          if (val.trim().length > 0) debouncedSearch(false);
        }}
        onBaseModelChange={(val) => {
          setBaseModel(val);
          setModelType(""); // Reset type when base model changes
        }}
        onModelTypeChange={(val) => {
          setModelType(val);
        }}
      />

      {/* Results list: collapse when a model is selected (detail takes space) */}
      <div
        ref={resultsRef}
        className="overflow-auto mb-1"
        style={{
          flex: selectedModelId ? "0 1 auto" : 1,
          maxHeight: selectedModelId ? "50%" : "none",
          minHeight: 0,
        }}
      >
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

        {hasMore && !loading && results.length > 0 && (
          <div ref={sentinelRef} style={{ height: 1 }} />
        )}

        {!loading && results.length === 0 && (
          <p className="text-muted small text-center mt-3">
            {shouldSearch()
              ? "No results found."
              : "Select a base model and type, or type a search query."}
          </p>
        )}
      </div>

      {/* Model detail */}
      {detailLoading ? (
        <div className="text-center py-2">
          <Spinner animation="border" size="sm" />
          <div className="text-muted small mt-1">
            Loading model details...
          </div>
        </div>
      ) : selectedModelData && (
        <div
          className="overflow-auto"
          style={{
            flex: 1,
            borderTop:
              "1px solid var(--separator-color)",
            paddingTop: 6,
          }}
        >
          <CivitaiModelDetail
            model={modelDetail}
            onDownload={handleDownload}
          />
        </div>
      )}

      {/* Active downloads */}
      {downloads.length > 0 && (
        <div
          className="mt-1 pt-1"
          style={{
            borderTop: "1px solid var(--separator-color)",
          }}
        >
          <small className="text-muted d-block mb-1">
            Downloads
          </small>
          {downloads.map((d) => (
            <div key={d.jobId} className="mb-1">
              <DownloadProgress
                jobId={d.jobId}
                label={d.label}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
