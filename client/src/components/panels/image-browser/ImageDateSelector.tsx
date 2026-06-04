import type { ImageDateInfo } from "../../../api/client";

export default function ImageDateSelector({
  dates,
  selectedDate,
  showLocal,
  localImageCount,
  onChange,
}: {
  dates: ImageDateInfo[];
  selectedDate: string | null;
  showLocal: boolean;
  localImageCount: number;
  onChange: (value: string | null, isLocal: boolean) => void;
}) {
  const hasLocalImages = localImageCount > 0;

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value || null;
    if (val === "__local__") {
      onChange(null, true);
      return;
    }
    onChange(val, false);
  };

  return (
    <select
      className="form-select form-select-sm mb-2"
      value={showLocal ? "__local__" : selectedDate ?? ""}
      onChange={handleChange}
    >
      {hasLocalImages && (
        <option value="__local__">
          Local Storage ({localImageCount})
        </option>
      )}
      {dates.length === 0 && !hasLocalImages && (
        <option value="">No images found</option>
      )}
      {dates.map((d) => (
        <option key={d.value} value={d.value}>
          {d.label}
        </option>
      ))}
    </select>
  );
}
