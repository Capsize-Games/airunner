import Spinner from "react-bootstrap/Spinner";
import CivitaiSearchBar from "./CivitaiSearchBar";
import CivitaiResultCard from "./CivitaiResultCard";
import { cancelCivitaiVersionThumbnails } from "../../../api/downloads";
import CivitaiModelDetailModal from "./CivitaiModelDetailModal";
import { useCivitaiPrefs } from "../../../hooks/useCivitaiPrefs";
import { useCivitaiSearch } from "./useCivitaiSearch";
import { useCivitaiDetail } from "./useCivitaiDetail";

export default function CivitaiBrowserPanel() {
  const {
    baseModel, setBaseModel,
    modelType, setModelType,
    selectedModelId, setSelectedModelId,
  } = useCivitaiPrefs();

  const detail = useCivitaiDetail(baseModel, modelType, selectedModelId);

  const search = useCivitaiSearch(baseModel, modelType, selectedModelId, (payload) => {
    // Forward streaming thumbnail updates (version images) to detail hook
    if (payload.model_id === selectedModelId) {
      detail.applyStreamingThumbnail(payload as Parameters<typeof detail.applyStreamingThumbnail>[0]);
    }
  });

  const handleSelectModel = async (modelId: number) => {
    if (selectedModelId !== null && selectedModelId !== modelId) {
      cancelCivitaiVersionThumbnails(selectedModelId).catch(() => {});
    }
    setSelectedModelId(modelId);
    await detail.fetchModelDetail(modelId);
  };

  return (
    <div className="d-flex flex-column h-100 p-2" style={{ position: "relative" }}>
      <h6 className="text-muted mb-2">CivitAI Browser</h6>

      <CivitaiSearchBar
        query={search.query}
        baseModel={baseModel}
        modelType={modelType}
        filterOptions={search.filterOptions}
        onQueryChange={search.handleQueryChange}
        onBaseModelChange={(val) => { setBaseModel(val); setModelType(""); }}
        onModelTypeChange={setModelType}
      />

      <div ref={search.resultsRef} className="overflow-auto" style={{ flex: 1, minHeight: 0 }}>
        {search.results.map((item) => (
          <CivitaiResultCard
            key={item.id}
            item={item}
            selected={selectedModelId === item.id}
            onSelect={handleSelectModel}
          />
        ))}
        {search.loading && (
          <div className="text-center py-2">
            <Spinner animation="border" size="sm" />
          </div>
        )}
        {!search.loading && search.results.length === 0 && (
          <p className="text-muted small text-center mt-3">
            {search.shouldSearch()
              ? "No results found."
              : "Select a base model and type, or type a search query."}
          </p>
        )}
      </div>

      {selectedModelId !== null && (
        <CivitaiModelDetailModal
          model={detail.modelDetail}
          loading={detail.detailLoading}
          baseModel={baseModel}
          modelType={modelType}
          onVersionChange={detail.handleRequestVersionThumbnails}
          onClose={() => {
            if (selectedModelId !== null) {
              cancelCivitaiVersionThumbnails(selectedModelId).catch(() => {});
            }
            setSelectedModelId(null);
            detail.setSelectedModelData(null);
          }}
        />
      )}
    </div>
  );
}
