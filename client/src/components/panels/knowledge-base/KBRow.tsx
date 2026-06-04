export default function KBRow({
  doc,
  onToggle,
  onDragStart,
}: {
  doc: { id: number; name: string; active: boolean; indexed: boolean };
  onToggle: (docId: number) => void;
  onDragStart: (e: React.DragEvent<HTMLTableRowElement>, docId: number) => void;
}) {
  return (
    <tr
      key={doc.id}
      draggable
      onDragStart={(e) => onDragStart(e, doc.id)}
      style={{ cursor: "grab" }}
    >
      <td
        className="text-truncate"
        style={{ maxWidth: 180 }}
        title={doc.name}
      >
        {doc.name}
      </td>
      <td style={{ textAlign: "center" }}>
        <span
          style={{ cursor: "pointer", display: "inline-block" }}
          onClick={() => onToggle(doc.id)}
          title={
            doc.active
              ? "Click to deactivate"
              : "Click to activate"
          }
        >
          {doc.active ? "✅" : "☐"}
        </span>
      </td>
      <td style={{ textAlign: "center" }}>
        {doc.indexed ? "✅" : "—"}
      </td>
      <td style={{ textAlign: "center" }}>—</td>
    </tr>
  );
}
