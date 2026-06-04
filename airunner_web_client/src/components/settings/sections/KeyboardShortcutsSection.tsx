import { useState, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import { queryResources } from "../../../api/client";
import type { ResourceRecord } from "../../../types/api";

export default function KeyboardShortcutsSection() {
  const [shortcuts, setShortcuts] = useState<ResourceRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await queryResources("ShortcutKeys");
        if (cancelled) return;
        setShortcuts(data.records ?? []);
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="text-center py-4">
        <Spinner animation="border" size="sm" />
      </div>
    );
  }

  if (shortcuts.length === 0) {
    return (
      <div>
        <h6 className="mb-3">Keyboard Shortcuts</h6>
        <p className="small text-muted">No shortcuts configured.</p>
      </div>
    );
  }

  return (
    <div>
      <h6 className="mb-3">Keyboard Shortcuts</h6>
      <p className="small text-muted mb-3">
        View and configure keyboard shortcuts for common actions.
      </p>

      <div className="d-flex flex-column gap-1">
        {shortcuts.map((sc, idx) => (
          <div
            key={sc.id ?? idx}
            className="bg-dark bg-opacity-25 rounded p-2 border border-secondary d-flex justify-content-between align-items-center"
          >
            <div>
              <div className="small" style={{ color: "var(--theme-text)" }}>
                {String(sc.display_name ?? "")}
              </div>
              {sc.description && (
                <div className="small text-muted">
                  {String(sc.description)}
                </div>
              )}
            </div>
            <kbd className="bg-dark text-light border border-secondary px-2 py-1 rounded">
              {String(sc.key ?? "")}
            </kbd>
          </div>
        ))}
      </div>
    </div>
  );
}
