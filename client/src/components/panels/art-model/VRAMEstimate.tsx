import ProgressBar from "react-bootstrap/ProgressBar";

export default function VRAMEstimate({
  vramGb,
}: {
  vramGb: number | null;
}) {
  if (vramGb === null || vramGb <= 0) return null;

  return (
    <div className="mt-2 mb-2">
      <small className="text-theme-secondary">
        Estimated VRAM: {vramGb.toFixed(1)} GB
      </small>
      <ProgressBar
        now={Math.min((vramGb / 24) * 100, 100)}
        variant={vramGb > 20 ? "danger" : "success"}
        className="mt-1"
        style={{ height: 6 }}
      />
    </div>
  );
}
