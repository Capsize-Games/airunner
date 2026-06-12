import Form from "react-bootstrap/Form";

interface EmbeddingRecord {
  id: number;
  name: string;
  path: string;
  enabled: boolean;
  trigger_words: string[];
  _inputText: string;
}

export default function EmbeddingItem({
  item,
  onToggle,
  onCopyWord,
  onDeleteWord,
  onAddWords,
  onInputChange,
  onInputKeyDown,
}: {
  item: EmbeddingRecord;
  onToggle: (id: number, enabled: boolean) => void;
  onCopyWord: (word: string) => void;
  onDeleteWord: (id: number, word: string) => void;
  onAddWords: (id: number) => void;
  onInputChange: (id: number, value: string) => void;
  onInputKeyDown: (e: React.KeyboardEvent, id: number) => void;
}) {
  return (
    <div
      key={item.id}
      className="mb-3 p-2 rounded"
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid #333",
      }}
    >
      <div className="d-flex align-items-center gap-2 mb-1">
        <Form.Check
          type="switch"
          checked={item.enabled}
          onChange={(e) => onToggle(item.id, e.target.checked)}
          id={`embed-enable-${item.id}`}
        />
        <span
          className="small"
          style={{
            color: item.enabled ? "#c8c8c8" : "#666",
          }}
        >
          {item.name}
        </span>
      </div>

      {Array.isArray(item.trigger_words) && item.trigger_words.length > 0 && (
        <div className="d-flex flex-wrap gap-1 mb-1">
          {item.trigger_words.map((word) => (
            <span
              key={word}
              onClick={() => onCopyWord(word)}
              title="Click to copy"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 3,
                background: "rgba(0,132,185,0.15)",
                border: "1px solid var(--bs-primary)",
                borderRadius: 10,
                padding: "2px 8px",
                fontSize: "0.75rem",
                color: "var(--theme-text)",
                cursor: "pointer",
              }}
            >
              <span
                style={{
                  cursor: "pointer",
                  color: "#ff5555",
                  fontSize: "0.85rem",
                  lineHeight: 1,
                  padding: "1px 2px",
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteWord(item.id, word);
                }}
                title="Remove trigger word"
              >
                ✕
              </span>
              {word}
            </span>
          ))}
        </div>
      )}

      <div className="d-flex gap-1">
        <Form.Control
          size="sm"
          type="text"
          placeholder="Add trigger words (comma-separated)..."
          value={item._inputText}
          onChange={(e) => onInputChange(item.id, e.target.value)}
          onKeyDown={(e) => onInputKeyDown(e, item.id)}
          style={{
            background: "#1a1a2e",
            color: "var(--theme-text)",
            borderColor: "#333",
            fontSize: "0.7rem",
          }}
        />
        <button
          className="btn btn-sm"
          onClick={() => onAddWords(item.id)}
          disabled={!item._inputText.trim()}
          style={{
            background: "var(--bs-primary)",
            border: "none",
            color: "#fff",
            fontSize: "0.7rem",
            padding: "2px 8px",
          }}
        >
          Add
        </button>
      </div>
    </div>
  );
}
