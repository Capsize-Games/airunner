import Form from "react-bootstrap/Form";

interface Props {
  performConversationSummary: boolean;
  summarizeAfterNTurns: number;
  onSummaryToggle: (v: boolean) => void;
  onTurnsChange: (v: number) => void;
}

export default function ConversationSection({
  performConversationSummary, summarizeAfterNTurns, onSummaryToggle, onTurnsChange,
}: Props) {
  return (
    <div className="p-2 mt-2" style={{ border: "1px solid #333", borderRadius: 6 }}>
      <span style={{ color: "var(--theme-text-secondary)", fontWeight: 600, fontSize: "0.85rem", display: "block", marginBottom: 8 }}>
        Conversation Summarization
      </span>
      <Form.Check
        type="switch"
        id="llm-perform-summary"
        label={<span style={{ color: "var(--theme-text-secondary)" }}>Auto-summarize long conversations</span>}
        checked={performConversationSummary}
        onChange={(e) => onSummaryToggle(e.target.checked)}
      />
      {performConversationSummary && (
        <Form.Group className="mt-2">
          <Form.Label style={{ color: "var(--theme-text-secondary)", fontSize: "0.8rem" }}>
            Summarize after <strong>{summarizeAfterNTurns}</strong> conversation turns
          </Form.Label>
          <Form.Range
            min={2} max={50} step={1}
            value={summarizeAfterNTurns}
            onChange={(e) => onTurnsChange(Number(e.target.value))}
            style={{ accentColor: "var(--theme-primary)" }}
          />
        </Form.Group>
      )}
    </div>
  );
}
