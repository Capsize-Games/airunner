import Form from "react-bootstrap/Form";

export default function AgentTextareas({
  botPersonality,
  systemInstructions,
  guardrailsPrompt,
  usePersonality,
  useSystemInstructions,
  useGuardrails,
  onChange,
  onBlur,
}: {
  botPersonality: string;
  systemInstructions: string;
  guardrailsPrompt: string;
  usePersonality: boolean;
  useSystemInstructions: boolean;
  useGuardrails: boolean;
  onChange: (key: string, value: string) => void;
  onBlur: () => void;
}) {
  return (
    <>
      {usePersonality && (
        <Form.Group className="mb-2">
          <Form.Label className="small">Bot Personality</Form.Label>
          <Form.Control
            as="textarea"
            rows={3}
            size="sm"
            value={botPersonality}
            onChange={(e) => onChange("botPersonality", e.target.value)}
            onBlur={onBlur}
            className="bg-dark text-light border-secondary"
          />
        </Form.Group>
      )}

      {useSystemInstructions && (
        <Form.Group className="mb-2">
          <Form.Label className="small">System Instructions</Form.Label>
          <Form.Control
            as="textarea"
            rows={3}
            size="sm"
            value={systemInstructions}
            onChange={(e) => onChange("systemInstructions", e.target.value)}
            onBlur={onBlur}
            className="bg-dark text-light border-secondary"
          />
        </Form.Group>
      )}

      {useGuardrails && (
        <Form.Group className="mb-2">
          <Form.Label className="small">Guardrails Prompt</Form.Label>
          <Form.Control
            as="textarea"
            rows={3}
            size="sm"
            value={guardrailsPrompt}
            onChange={(e) => onChange("guardrailsPrompt", e.target.value)}
            onBlur={onBlur}
            className="bg-dark text-light border-secondary"
          />
        </Form.Group>
      )}
    </>
  );
}
