import type { ActiveModelInfo } from "../../../api/client";
import LucideIcon from "../../shared/LucideIcon";
import type { ModelSlot } from "./useStatsPanel";

interface Props {
  slots: ModelSlot[];
  loadingRef: React.MutableRefObject<Set<string>>;
  findModel: (type: string) => ActiveModelInfo | undefined;
  statusColor: (status: string) => string;
  onLoad: (type: string, id: string) => void;
  onUnload: (m: ActiveModelInfo, slotType: string) => void;
}

export default function ModelSlotList({
  slots, loadingRef, findModel, statusColor, onLoad, onUnload,
}: Props) {
  return (
    <div className="mt-2">
      <small className="text-muted d-block mb-1">Models</small>
      {slots.map(({ type, label, name, canLoad }) => {
        const m = findModel(type);
        const status = m?.status ?? "unloaded";
        return (
          <div
            key={type}
            className="d-flex align-items-center justify-content-between mb-1"
            style={{ fontSize: "11px" }}
          >
            <span className="text-truncate" style={{ maxWidth: "70%" }}>
              <span style={{
                display: "inline-block", width: 8, height: 8,
                borderRadius: "50%", backgroundColor: statusColor(status),
                marginRight: 4, flexShrink: 0,
              }} />
              {label}: {name || "none"}
            </span>
            {status === "loading" || (status !== "loaded" && loadingRef.current.has(type)) ? (
              <span style={{ display: "flex", opacity: 0.5 }}>
                <LucideIcon name="loader" size={14} />
              </span>
            ) : m?.can_unload ? (
              <button className="model-action-btn" onClick={() => onUnload(m, type)} title={`Unload ${label}`}>
                <LucideIcon name="octagon-alert" size={14} />
              </button>
            ) : canLoad ? (
              <button className="model-action-btn" onClick={() => onLoad(type, name)} title={`Load ${label}`}>
                <LucideIcon name="play" size={14} />
              </button>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
