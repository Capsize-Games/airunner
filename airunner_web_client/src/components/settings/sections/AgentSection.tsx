import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  queryFirstResource,
  updateResource,
} from "../../../api/client";
import type { ResourceRecord } from "../../../types/api";

const GENDER_OPTIONS = ["Male", "Female"];

export default function AgentSection() {
  const [agents] = useState<ResourceRecord[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [botname, setBotname] = useState("");
  const [botPersonality, setBotPersonality] = useState("");
  const [systemInstructions, setSystemInstructions] = useState("");
  const [guardrailsPrompt, setGuardrailsPrompt] = useState("");
  const [useSystemInstructions, setUseSystemInstructions] = useState(true);
  const [useGuardrails, setUseGuardrails] = useState(true);
  const [usePersonality, setUsePersonality] = useState(true);
  const [assignNames, setAssignNames] = useState(true);
  const [useDatetime, setUseDatetime] = useState(true);
  const [gender, setGender] = useState("Male");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        // Try to get current agent first
        const current = await queryFirstResource("Chatbot", {
          current: true,
        } as Record<string, unknown>).catch(() => null);
        if (cancelled) return;

        if (current?.record) {
          applyRecord(current.record);
          setSelectedId(current.record.id as number ?? null);
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
    setBotname(String(r.botname ?? ""));
    setBotPersonality(String(r.bot_personality ?? ""));
    setSystemInstructions(String(r.system_instructions ?? ""));
    setGuardrailsPrompt(String(r.guardrails_prompt ?? ""));
    setUseSystemInstructions(r.use_system_instructions !== false);
    setUseGuardrails(r.use_guardrails !== false);
    setUsePersonality(r.use_personality !== false);
    setAssignNames(r.assign_names !== false);
    setUseDatetime(r.use_datetime !== false);
    setGender(String(r.gender ?? "Male"));
  }

  function persistAll() {
    if (!selectedId) return;
    updateResource("Chatbot", selectedId, {
      botname,
      bot_personality: botPersonality,
      system_instructions: systemInstructions,
      guardrails_prompt: guardrailsPrompt,
      use_system_instructions: useSystemInstructions,
      use_guardrails: useGuardrails,
      use_personality: usePersonality,
      assign_names: assignNames,
      use_datetime: useDatetime,
      gender,
    } as Record<string, unknown>).catch(() => {});
  }

  if (loading) {
    return (
      <div className="text-center py-4">
        <Spinner animation="border" size="sm" />
      </div>
    );
  }

  return (
    <div>
      <h6 className="mb-3">Agent Preferences</h6>

      <div className="mb-3">
        <Form.Group className="mb-2">
          <Form.Label className="small">Bot Name</Form.Label>
          <Form.Control
            size="sm"
            value={botname}
            onChange={(e) => setBotname(e.target.value)}
            onBlur={persistAll}
            className="bg-dark text-light border-secondary"
          />
        </Form.Group>

        <Form.Group className="mb-2">
          <Form.Check
            type="switch"
            label="Use personality"
            checked={usePersonality}
            onChange={(e) => {
              setUsePersonality(e.target.checked);
              if (selectedId) {
                updateResource("Chatbot", selectedId, {
                  use_personality: e.target.checked,
                } as Record<string, unknown>).catch(() => {});
              }
            }}
            className="small"
          />
        </Form.Group>
        {usePersonality && (
          <Form.Group className="mb-2">
            <Form.Label className="small">Bot Personality</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              size="sm"
              value={botPersonality}
              onChange={(e) => setBotPersonality(e.target.value)}
              onBlur={persistAll}
              className="bg-dark text-light border-secondary"
            />
          </Form.Group>
        )}

        <Form.Group className="mb-2">
          <Form.Check
            type="switch"
            label="Use system instructions"
            checked={useSystemInstructions}
            onChange={(e) => {
              setUseSystemInstructions(e.target.checked);
              if (selectedId) {
                updateResource("Chatbot", selectedId, {
                  use_system_instructions: e.target.checked,
                } as Record<string, unknown>).catch(() => {});
              }
            }}
            className="small"
          />
        </Form.Group>
        {useSystemInstructions && (
          <Form.Group className="mb-2">
            <Form.Label className="small">System Instructions</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              size="sm"
              value={systemInstructions}
              onChange={(e) => setSystemInstructions(e.target.value)}
              onBlur={persistAll}
              className="bg-dark text-light border-secondary"
            />
          </Form.Group>
        )}

        <Form.Group className="mb-2">
          <Form.Check
            type="switch"
            label="Use guardrails"
            checked={useGuardrails}
            onChange={(e) => {
              setUseGuardrails(e.target.checked);
              if (selectedId) {
                updateResource("Chatbot", selectedId, {
                  use_guardrails: e.target.checked,
                } as Record<string, unknown>).catch(() => {});
              }
            }}
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
              onBlur={persistAll}
              className="bg-dark text-light border-secondary"
            />
          </Form.Group>
        )}

        <Form.Group className="mb-2">
          <Form.Check
            type="switch"
            label="Assign names"
            checked={assignNames}
            onChange={(e) => {
              setAssignNames(e.target.checked);
              if (selectedId) {
                updateResource("Chatbot", selectedId, {
                  assign_names: e.target.checked,
                } as Record<string, unknown>).catch(() => {});
              }
            }}
            className="small"
          />
        </Form.Group>

        <Form.Group className="mb-2">
          <Form.Check
            type="switch"
            label="Use datetime in prompts"
            checked={useDatetime}
            onChange={(e) => {
              setUseDatetime(e.target.checked);
              if (selectedId) {
                updateResource("Chatbot", selectedId, {
                  use_datetime: e.target.checked,
                } as Record<string, unknown>).catch(() => {});
              }
            }}
            className="small"
          />
        </Form.Group>

        <Form.Group className="mb-2">
          <Form.Label className="small">Gender</Form.Label>
          <Form.Select
            size="sm"
            value={gender}
            onChange={(e) => {
              setGender(e.target.value);
              if (selectedId) {
                updateResource("Chatbot", selectedId, {
                  gender: e.target.value,
                } as Record<string, unknown>).catch(() => {});
              }
            }}
            className="bg-dark text-light border-secondary"
          >
            {GENDER_OPTIONS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </Form.Select>
        </Form.Group>
      </div>
    </div>
  );
}
