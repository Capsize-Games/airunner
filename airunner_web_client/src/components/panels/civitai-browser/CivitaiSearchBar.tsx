import { type FormEvent } from "react";
import { BASE_MODEL_OPTIONS, MODEL_TYPE_OPTIONS } from "./constants";

interface CivitaiSearchBarProps {
  query: string;
  baseModel: string;
  modelType: string;
  onQueryChange: (val: string) => void;
  onBaseModelChange: (val: string) => void;
  onModelTypeChange: (val: string) => void;
  onSearch: () => void;
}

export default function CivitaiSearchBar({
  query,
  baseModel,
  modelType,
  onQueryChange,
  onBaseModelChange,
  onModelTypeChange,
  onSearch,
}: CivitaiSearchBarProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSearch();
  };

  const modelTypes = baseModel
    ? MODEL_TYPE_OPTIONS[baseModel] ?? []
    : [];

  // Reset model type when base model changes and current type not in new list
  const currentTypeValid = modelTypes.some(
    (t) => t.value === modelType,
  );
  if (modelType && modelType !== "" && !currentTypeValid) {
    // We don't call onModelTypeChange here to avoid side-effects during render
  }

  return (
    <form onSubmit={handleSubmit} className="mb-2">
      <div className="input-group input-group-sm mb-1">
        <input
          className="form-control"
          placeholder="Search CivitAI..."
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          style={{ fontSize: 12 }}
        />
      </div>
      <div className="d-flex gap-1">
        <select
          className="form-select form-select-sm"
          value={baseModel}
          onChange={(e) => onBaseModelChange(e.target.value)}
          style={{ fontSize: 11, flex: 1 }}
        >
          <option value="">All base models</option>
          {BASE_MODEL_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <select
          className="form-select form-select-sm"
          value={modelType}
          onChange={(e) => onModelTypeChange(e.target.value)}
          style={{ fontSize: 11, flex: 1 }}
        >
          <option value="">All types</option>
          {modelTypes.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="btn btn-sm btn-outline-primary"
          style={{ fontSize: 11, whiteSpace: "nowrap" }}
        >
          Search
        </button>
      </div>
    </form>
  );
}
