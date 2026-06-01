import { useEffect, useState } from "react";
import Card from "react-bootstrap/Card";
import ProgressBar from "react-bootstrap/ProgressBar";
import { getHardwareProfile } from "../../api/client";
import type { HardwareProfile } from "../../types/api";

export default function RightSidebar() {
  const [hw, setHw] = useState<HardwareProfile | null>(null);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const profile = await getHardwareProfile();
        if (active) setHw(profile);
      } catch {
        // unavailable
      }
    };
    poll();
    const timer = setInterval(poll, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  if (!hw) {
    return (
      <aside className="right-sidebar p-3">
        <Card body className="text-muted small">
          Hardware info unavailable.
        </Card>
      </aside>
    );
  }

  const vramPct =
    hw.total_vram_gb > 0
      ? ((hw.total_vram_gb - hw.available_vram_gb) / hw.total_vram_gb) * 100
      : 0;
  const ramPct =
    hw.total_ram_gb > 0
      ? ((hw.total_ram_gb - hw.available_ram_gb) / hw.total_ram_gb) * 100
      : 0;

  return (
    <aside className="right-sidebar p-3">
      <Card className="mb-2">
        <Card.Body>
          <Card.Title className="fs-6">🖥️ Hardware</Card.Title>
          <small>{hw.device_name ?? "No GPU"} · {hw.cpu_count} cores</small>
        </Card.Body>
      </Card>
      <Card className="mb-2">
        <Card.Body>
          <strong className="small">VRAM</strong>
          <ProgressBar
            now={Math.min(vramPct, 100)}
            label={`${hw.available_vram_gb.toFixed(1)} / ${hw.total_vram_gb.toFixed(1)} GB`}
            variant={vramPct > 90 ? "danger" : "success"}
            className="mt-1"
          />
        </Card.Body>
      </Card>
      <Card>
        <Card.Body>
          <strong className="small">RAM</strong>
          <ProgressBar
            now={Math.min(ramPct, 100)}
            label={`${hw.available_ram_gb.toFixed(1)} / ${hw.total_ram_gb.toFixed(1)} GB`}
            variant={ramPct > 90 ? "danger" : "info"}
            className="mt-1"
          />
        </Card.Body>
      </Card>
    </aside>
  );
}
