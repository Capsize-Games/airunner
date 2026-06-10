import { useStatsPanel } from "./stats/useStatsPanel";
import MemoryBar from "./stats/MemoryBar";
import ModelSlotList from "./stats/ModelSlotList";

const panelStyle: React.CSSProperties = {
  background: "#1a1a2e", border: "1px solid #444", borderRadius: 6,
  padding: "10px 12px", width: 280, fontFamily: "monospace",
  color: "#ccc", fontSize: 12, boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
};

export default function StatsPanel() {
  const { hw, slots, loadingRef, unloadingSlots, findModel, statusColor, handleLoad, handleUnload } = useStatsPanel();

  if (!hw) {
    return (
      <div style={panelStyle}>
        <h6 className="text-muted mb-2">Model Resources</h6>
        <p className="text-muted small">Hardware info unavailable.</p>
      </div>
    );
  }

  const vramUsed = hw.total_vram_gb > 0 ? hw.total_vram_gb - hw.available_vram_gb : 0;
  const ramUsed = hw.total_ram_gb > 0 ? hw.total_ram_gb - hw.available_ram_gb : 0;

  return (
    <div style={panelStyle}>
      <h6 className="text-muted mb-2">Model Resources</h6>
      <div className="small text-muted mb-2">
        {hw.device_name ?? "CPU"} &middot; {hw.cpu_count} cores &middot; {hw.num_gpus} GPU(s)
      </div>

      <MemoryBar
        label="VRAM"
        usedGb={vramUsed}
        totalGb={hw.total_vram_gb}
        highColor="var(--bs-danger)"
        lowColor="var(--bs-success)"
      />
      <MemoryBar
        label="RAM"
        usedGb={ramUsed}
        totalGb={hw.total_ram_gb}
        highColor="var(--bs-danger)"
        lowColor="var(--bs-info)"
      />

      <ModelSlotList
        slots={slots}
        loadingRef={loadingRef}
        unloadingSlots={unloadingSlots}
        findModel={findModel}
        statusColor={statusColor}
        onLoad={handleLoad}
        onUnload={handleUnload}
      />
    </div>
  );
}
