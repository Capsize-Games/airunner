import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import {
  queryResources,
  updateResource,
} from "../../api/client";
import type { ResourceRecord } from "../../types/api";

export default function PromptTemplatesSection() {
  const [templates, setTemplates] = useState<ResourceRecord[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [guardrailsPrompt, setGuardrailsPrompt] = useState("");
  const [useGuardrails, setUseGuardrails] = useState(true);
  const [useDatetime, setUseDatetime] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await queryResources("PromptTemplate");
        if (cancelled) return;
        setTemplates(data.records ?? []);
        if (data.records && data.records.length > 0) {
          applyRecord(data.records[0]);
          setSelectedId(data.records[0].id as number ?? null);
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function applyRecord(r: ResourceRecord) {
    setSystemPrompt(String(r.system ?? ""));
    setGuardrailsPrompt(String(r.guardrails ?? ""));
    setUseGuardrails(r.use_guardrails !== false);
    setUseDatetime(r.use_system_datetime_in_system_prompt === true);
  }

  function handleSelect(id: number) {
    const tpl = templates.find((t) => t.id === id);
    if (tpl) {
      setSelectedId(id);
      applyRecord(tpl);
    }
  }

  async function handleSave() {
    if (!selectedId) return;
    setSaving(true);
    try {
      await updateResource("PromptTemplate", selectedId, {
        system: systemPrompt,
        guardrails: guardrailsPrompt,
        use_guardrails: useGuardrails,
        use_system_datetime_in_system_prompt: useDatetime,
      } as Record<string, unknown>);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="text-center py-4">
        <Spinner animation="border" size="sm" />
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div>
        <h6 className="mb-3">Prompt Templates</h6>
        <p className="small text-muted">No templates available.</p>
      </div>
    );
  }

  const selected = templates.find((t) => t.id === selectedId);

  return (
    <div>
      <h6 className="mb-3">Prompt Templates</h6>

      <Form.Group className="mb-3">
        <Form.Label className="small">Template</Form.Label>
        <Form.Select
          size="sm"
          value={selectedId ?? ""}
          onChange={(e) => handleSelect(Number(e.target.value))}
          className="bg-dark text-light border-secondary"
        >
          {templates.map((tpl) => (
            <option key={tpl.id as number} value={tpl.id as number}>
              {String(tpl.template_name ?? "")}
            </option>
          ))}
        </Form.Select>
      </Form.Group>

      {selected && (
        <>
          <Form.Group className="mb-2">
            <Form.Label className="small">System Prompt</Form.Label>
            <Form.Control
              as="textarea"
              rows={4}
              size="sm"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="bg-dark text-light border-secondary"
            />
          </Form.Group>

          <Form.Group className="mb-2">
            <Form.Check
              type="switch"
              label="Use guardrails"
              checked={useGuardrails}
              onChange={(e) => setUseGuardrails(e.target.checked)}
              className="small"
            />
          </Form.Group>

          {useGuardrails && (
            <Form.Group className="mb-2">
              <Form.Label className="small">Guardrails Prompt</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                size="sm"
                value={guardrailsPrompt}
                onChange={(e) => setGuardrailsPrompt(e.target.value)}
                className="bg-dark text-light border-secondary"
              />
            </Form.Group>
          )}

          <Form.Group className="mb-3">
            <Form.Check
              type="switch"
              label="Use datetime in system prompt"
              checked={useDatetime}
              onChange={(e) => setUseDatetime(e.target.checked)}
              className="small"
            />
          </Form.Group>
        </>
      )}

      <Button
        variant="primary"
        size="sm"
        onClick={handleSave}
        disabled={saving || !selectedId}
      >
        {saving ? <Spinner animation="border" size="sm" /> : "Save"}
      </Button>
    </div>
  );
}
