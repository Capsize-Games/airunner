import { useState, useEffect, useCallback } from "react";
import { useDb } from "../db/DbContext";

interface DateOption { value: string; label: string; }

// ── useImageDates ─────────────────────────────────────────────────────────────
// Caches the list of image dates in IndexedDB.  The list only changes when
// the user generates new images (EVENT_IMAGES triggers reload).  On mount we
// serve the cached list immediately, then refresh from the server.

export function useImageDates() {
  const db = useDb();
  const [dates, setDates] = useState<DateOption[]>([]);
  const [loading, setLoading] = useState(true);

  const toCached = (d: DateOption) => ({ date: d.value, cachedAt: Date.now() });

  const load = useCallback(async () => {
    if (db) {
      // Serve cached dates immediately.
      try {
        const cached = await db.imageDates.orderBy("date").reverse().toArray();
        if (cached.length > 0) {
          setDates(cached.map((r) => ({ value: r.date, label: r.date })));
          setLoading(false);
        }
      } catch { /* unavailable */ }
    }

    // Fetch from server.
    try {
      const { listImageDates } = await import("../api/client");
      const data = await listImageDates();
      const fresh: DateOption[] = data.dates ?? [];
      setDates(fresh);

      if (db) {
        await db.imageDates.bulkPut(fresh.map(toCached));
        // Remove dates that no longer exist on the server.
        const freshSet = new Set(fresh.map((d) => d.value));
        const allCached = await db.imageDates.toArray();
        const toDelete = allCached
          .filter((r) => !freshSet.has(r.date))
          .map((r) => r.date);
        if (toDelete.length > 0) await db.imageDates.bulkDelete(toDelete);
      }
    } catch { /* network unavailable — stale cache shown */ } finally {
      setLoading(false);
    }
  }, [db]);

  useEffect(() => {
    load();
  }, [load]);

  return { dates, loading, reload: load };
}
