import { useState, useRef, useCallback } from "react";
import Spinner from "react-bootstrap/Spinner";
import CivitaiSearchBar from "./CivitaiSearchBar";
import CivitaiResultCard from "./CivitaiResultCard";
import CivitaiModelDetail from "./CivitaiModelDetail";
import DownloadProgress from "../../downloads/DownloadProgress";
import { searchCivitaiModels, fetchCivitaiModel, startCivitaiFileDownload } from "../../../api/downloads";
import type { JsonObject } from "../../../types/api";

interface SearchResult {
  id: number;
  name: string;
  type?: string;
  baseModel?: string;
  creator?: string;
  thumbnail?: string;
}

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

  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [selectedModelData, setSelectedModelData] = useState<JsonObject | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [downloads, setDownloads] = useState<DownloadJob[]>([]);

  // Cache for model details keyed by model_id
  const detailCache = useRef<Map<number, JsonObject>>(new Map());

  const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

  const doSearch = useCallback(
    async (append = false) => {
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
        const items: SearchResult[] = ((data.items ?? []) as JsonObject[]).map(
          (item: JsonObject) => ({
            id: Number(item.id),
            name: String(item.name ?? ""),
            type: item.type ? String(item.type) : undefined,
            baseModel: item.baseModel
              ? String(item.baseModel)
              : undefined,
            creator: item.creator
              ? String(item.creator)
              : undefined,
            thumbnail: item.thumbnail
              ? String(item.thumbnail)
              : undefined,
          }),
        );
        if (append) {
          setResults((prev) => [...prev, ...items]);
        } else {
          setResults(items);
        }
        const meta = data.metadata as JsonObject | undefined;
        setCursor((meta?.nextCursor as string) ?? null);
        setHasMore(!!meta?.nextCursor);
      } catch {
        // search failed
      } finally {
        setLoading(false);
      }
    },
    [query, baseModel, modelType, cursor],
  );

  const handleSearch = () => {
    setCursor(null);
    doSearch(false);
  };

  const handleLoadMore = () => {
    if (hasMore && !loading) {
      doSearch(true);
    }
  };

  const handleSelectModel = useCallback(
    async (modelId: number) => {
      setSelectedModelId(modelId);
      // Check cache
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
        // failed to load detail
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
      const basePath = "/tmp/airunner/downloads"; // simplified; real path from settings
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

  // Convert JsonObject to the shape expected by CivitaiModelDetail
  const modelDetail = selectedModelData
    ? {
        id: Number((selectedModelData as JsonObject).id ?? 0),
        name: String((selectedModelData as JsonObject).name ?? ""),
        description: (selectedModelData as JsonObject).description
          ? String((selectedModelData as JsonObject).description)
          : undefined,
        creator: (selectedModelData as JsonObject).creator
          ? String((selectedModelData as JsonObject).creator)
          : undefined,
        type: (selectedModelData as JsonObject).type
          ? String((selectedModelData as JsonObject).type)
          : undefined,
        stats: (selectedModelData as JsonObject).stats as
          | {
              downloadCount?: number;
              favoriteCount?: number;
              commentCount?: number;
            }
          | undefined,
        versions: ((selectedModelData as JsonObject).versions ??
          []) as {
          id: number;
          name: string;
          baseModel?: string;
          files?: {
            id: number;
            name: string;
            sizeKB?: number;
            downloadUrl?: string;
          }[];
          images?: { url: string; nsfw?: string; width?: number; height?: number }[];
          downloadUrl?: string;
        }[],
      }
    : null;

  return (
    <div className="d-flex flex-column h-100 p-2">
      <h6 className="text-muted mb-2">CivitAI Browser</h6>

      {/* Search */}
      <CivitaiSearchBar
        query={query}
        baseModel={baseModel}
        modelType={modelType}
        onQueryChange={setQuery}
        onBaseModelChange={setBaseModel}
        onModelTypeChange={setModelType}
        onSearch={handleSearch}
      />

      {/* Results list */}
      <div
        className="overflow-auto mb-1"
        style={{ flex: 1, minHeight: 0 }}
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
          <button
            className="btn btn-sm btn-outline-secondary w-100 mt-1"
            onClick={handleLoadMore}
            style={{ fontSize: 11 }}
          >
            Load More
          </button>
        )}

        {!loading && results.length === 0 && (
          <p className="text-muted small text-center mt-3">
            {query || baseModel || modelType
              ? "No results found."
              : "Use the search bar above to browse CivitAI models."}
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
      ) : (
        <div
          className="overflow-auto"
          style={{ maxHeight: "45%", borderTop: "1px solid var(--separator-color)", paddingTop: 6 }}
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
