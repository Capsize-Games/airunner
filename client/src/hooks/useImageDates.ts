import { useState, useEffect, useCallback } from "react";

interface DateOption { value: string; label: string; }

// ── useImageDates ─────────────────────────────────────────────────────────────
// Server-only: always fetches from the API.

export function useImageDates() {
  const [dates, setDates] = useState<DateOption[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { listImageDates } = await import("../api/client");
      const data = await listImageDates();
      setDates(data.dates ?? []);
    } catch { /* network unavailable */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { dates, loading, reload: load };
}
