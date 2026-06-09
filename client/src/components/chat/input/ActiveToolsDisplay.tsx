export default function ActiveToolsDisplay({
  activeTools,
}: {
  activeTools: Array<{ tool_id: string; tool_name: string }>;
}) {
  if (activeTools.length === 0) return null;
  return (
    <div
      className="border-t-subtle"
      style={{
        padding: "2px 10px",
        fontSize: "0.72rem",
        color: "var(--bs-info)",
        background: "rgba(13,202,240,0.04)",
      }}
    >
      {activeTools.map((t) => (
        <div key={t.tool_id} className="d-flex align-items-center gap-1">
          <span>⚙</span>
          <span>{t.tool_name} running…</span>
        </div>
      ))}
    </div>
  );
}
