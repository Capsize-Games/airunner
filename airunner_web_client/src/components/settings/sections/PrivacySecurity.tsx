import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getPrivacySettings,
  updatePrivacySettings,
  getSingleton,
  updateSingleton,
} from "../../../api/client";

interface ServiceRow {
  key: string;
  label: string;
  apiKeyField?: string;
}

const SERVICE_ROWS: ServiceRow[] = [
  { key: "huggingface", label: "HuggingFace",
    apiKeyField: "hf_api_key_read_key" },
  { key: "civitai", label: "CivitAI",
    apiKeyField: "civit_ai_api_key" },
  { key: "openrouter", label: "OpenRouter",
    apiKeyField: "openrouter_api_key" },
  { key: "openai", label: "OpenAI",
    apiKeyField: "openai_api_key" },
  { key: "duckduckgo", label: "DuckDuckGo" },
  { key: "openmeteo", label: "Open-Meteo" },
];

export default function PrivacySecuritySection() {
  const [services, setServices] = useState<Record<string, boolean>>({});
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [privacy, appSettings] = await Promise.all([
          getPrivacySettings(),
          getSingleton("ApplicationSettings"),
        ]);
        if (cancelled) return;
        setServices(privacy.services ?? {});
        setApiKeys({
          hf_api_key_read_key: String(
            appSettings.hf_api_key_read_key ?? "",
          ),
          civit_ai_api_key: String(
            appSettings.civit_ai_api_key ?? "",
          ),
          openrouter_api_key: String(
            appSettings.openrouter_api_key ?? "",
          ),
          openai_api_key: String(
            appSettings.openai_api_key ?? "",
          ),
        });
      } catch {
        // silently fail
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function handleToggle(key: string, checked: boolean) {
    const next = { ...services, [key]: checked };
    setServices(next);
    updatePrivacySettings(next).catch(() => {});
  }

  function handleKeyChange(key: string, value: string) {
    setApiKeys((prev) => ({ ...prev, [key]: value }));
  }

  function handleKeyBlur() {
    const payload: Record<string, unknown> = {};
    for (const row of SERVICE_ROWS) {
      if (row.apiKeyField) {
        payload[row.apiKeyField] = apiKeys[row.apiKeyField] || null;
      }
    }
    updateSingleton(
      "ApplicationSettings",
      payload as Record<string, unknown>,
    ).catch(() => {});
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
      <h6 className="mb-3">Third-party Services</h6>

      <table
        style={{ width: "100%", borderCollapse: "collapse" }}
      >
        <thead>
          <tr>
            <th
              style={{
                width: 120,
                textAlign: "left",
                padding: "4px 8px 4px 0",
                fontSize: 11,
                color: "#666",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              Service
            </th>
            <th
              style={{
                textAlign: "left",
                padding: "4px 8px",
                fontSize: 11,
                color: "#666",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              API Key
            </th>
            <th
              style={{
                width: 80,
                textAlign: "center",
                padding: "4px 0 4px 8px",
                fontSize: 11,
                color: "#666",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              Enable
            </th>
          </tr>
        </thead>
        <tbody>
          {SERVICE_ROWS.map((row) => (
            <tr key={row.key}>
              <td
                style={{
                  padding: "4px 8px 4px 0",
                  verticalAlign: "middle",
                  color: "#a0a0a8",
                  fontSize: 13,
                }}
              >
                {row.label}
              </td>
              <td style={{ padding: "3px 8px" }}>
                {row.apiKeyField ? (
                  <Form.Control
                    type="password"
                    size="sm"
                    value={apiKeys[row.apiKeyField] ?? ""}
                    onChange={(e) =>
                      handleKeyChange(
                        row.apiKeyField!,
                        e.target.value,
                      )
                    }
                    onBlur={handleKeyBlur}
                    className="bg-dark text-light border-secondary"
                    placeholder={`${row.label} API key`}
                  />
                ) : (
                  <span
                    style={{
                      color: "#555",
                      fontSize: 12,
                      fontStyle: "italic",
                    }}
                  >
                    No API key required
                  </span>
                )}
              </td>
              <td
                style={{
                  padding: "3px 0 3px 8px",
                  textAlign: "center",
                  verticalAlign: "middle",
                }}
              >
                <Form.Check
                  type="switch"
                  checked={!!services[row.key]}
                  onChange={(e) =>
                    handleToggle(row.key, e.target.checked)
                  }
                  id={`enable-${row.key}`}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
