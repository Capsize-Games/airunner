import { useState, useEffect } from "react";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  getSingleton,
  updateSingleton,
} from "../../../api/client";

export default function UserSection() {
  const [username, setUsername] = useState("");
  const [zipcode, setZipcode] = useState("");
  const [unitSystem, setUnitSystem] = useState("imperial");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const user = await getSingleton("User");
        if (cancelled) return;
        setUsername(String(user.username ?? ""));
        setZipcode(String(user.zipcode ?? ""));
        setUnitSystem(String(user.unit_system ?? "imperial"));
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  async function persistUser() {
    await updateSingleton("User", {
      username: username || null,
      zipcode: zipcode || null,
      unit_system: unitSystem,
    } as Record<string, unknown>).catch(() => {});
  }

  function handleUnitSystemChange(value: string) {
    setUnitSystem(value);
    updateSingleton("User", {
      username: username || null,
      zipcode: zipcode || null,
      unit_system: value,
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
      <h6 className="mb-3">User Settings</h6>

      <Form.Group className="mb-2">
        <Form.Label className="small">Username</Form.Label>
        <Form.Control
          size="sm"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onBlur={persistUser}
          className="bg-dark text-light border-secondary"
          placeholder="Your display name"
        />
      </Form.Group>

      <Form.Group className="mb-2">
        <Form.Label className="small">Zipcode</Form.Label>
        <Form.Control
          size="sm"
          value={zipcode}
          onChange={(e) => setZipcode(e.target.value)}
          onBlur={persistUser}
          className="bg-dark text-light border-secondary"
          placeholder="e.g. 90210"
        />
      </Form.Group>

      <Form.Group className="mb-3">
        <Form.Label className="small">Unit System</Form.Label>
        <Form.Select
          size="sm"
          value={unitSystem}
          onChange={(e) => handleUnitSystemChange(e.target.value)}
          className="bg-dark text-light border-secondary"
        >
          <option value="imperial">Imperial</option>
          <option value="metric">Metric</option>
        </Form.Select>
      </Form.Group>
    </div>
  );
}
