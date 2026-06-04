import { type FormEvent } from "react";

interface FilterOption {
  label: string;
  value: string;
}

interface CivitaiSearchBarProps {
  query: string;
  baseModel: string;
  modelType: string;
  filterOptions: {
    baseModels: FilterOption[];
    typesByBase: Record<string, string[]>;
  };
  onQueryChange: (val: string) => void;
  onBaseModelChange: (val: string) => void;
  onModelTypeChange: (val: string) => void;
}

export default function CivitaiSearchBar({
  query,
  baseModel,
  modelType,
  filterOptions,
  onQueryChange,
  onBaseModelChange,
  onModelTypeChange,
}: CivitaiSearchBarProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
  };

  const modelTypes = baseModel
    ? filterOptions.typesByBase[baseModel] ?? []
    : [];

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
          {filterOptions.baseModels.map((opt) => (
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
          {modelTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>
    </form>
  );
}
