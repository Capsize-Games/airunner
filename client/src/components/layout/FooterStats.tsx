// ── Footer Stats ────────────────────────────────────────────────────────
import { useState, useEffect, lazy, Suspense } from "react";
import type { HardwareProfile } from "../../types/api";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_HARDWARE } from "../../features/events/types";

const StatsPanel = lazy(() => import("../panels/StatsPanel"));

export default function FooterStats() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  // One fetch on mount for an immediate readout; after that the server
  // pushes `hardware` events (sampled once server-side and broadcast to all
  // clients) instead of every client polling the endpoint.
  useEffect(() => {
    let canceled = false;
    (async () => {
      try {
        const { getHardwareProfile } = await import("../../api/client");
        const data = await getHardwareProfile();
        if (!canceled) setHw(data);
      } catch {
        /* server may be unavailable */
      }
    })();
    return () => {
      canceled = true;
    };
  }, []);

  useEventBus([EVENT_HARDWARE], (_event, data) => {
    setHw(data as HardwareProfile);
  });

  if (!hw || hw.total_vram_gb === 0) return null;

  const vramUsed =
    hw.total_vram_gb - hw.available_vram_gb;
  const vramPct =
    (vramUsed / hw.total_vram_gb) * 100;
  const ramUsed =
    hw.total_ram_gb - hw.available_ram_gb;
  const ramPct =
    (ramUsed / hw.total_ram_gb) * 100;

  const color = (pct: number) =>
    pct > 90
      ? "#dc3545"
      : pct > 70
        ? "#ffc107"
        : "rgba(255,255,255,0.4)";

  return (
    <span
      style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
      }}
    >
      <button
        onClick={() => setShowDetail((v) => !v)}
        title="Resource monitor"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontFamily: "monospace",
          fontSize: 11,
        }}
      >
        <span style={{ color: color(vramPct) }}>
          VRAM {vramUsed.toFixed(1)}/
          {hw.total_vram_gb.toFixed(0)}GB
        </span>
        <span
          style={{
            color: "rgba(255,255,255,0.2)",
          }}
        >
          ·
        </span>
        <span style={{ color: color(ramPct) }}>
          RAM {ramUsed.toFixed(1)}/
          {hw.total_ram_gb.toFixed(0)}GB
        </span>
      </button>
      {showDetail && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            right: 0,
            zIndex: 9999,
          }}
        >
          <Suspense fallback={null}>
            <StatsPanel />
          </Suspense>
        </div>
      )}
    </span>
  );
}
