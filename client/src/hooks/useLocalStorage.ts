import { useState, useCallback } from "react";

// ── useLocalStorage ───────────────────────────────────────────────────────────
// Typed localStorage hook with synchronous initialisation (safe for reading on
// first render) and a stable setter that persists on every call.

export function useLocalStorage<T>(
  key: string,
  defaultValue: T,
): [T, (value: T) => void] {
  const [value, setValueState] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return defaultValue;
      return JSON.parse(raw) as T;
    } catch {
      return defaultValue;
    }
  });

  const setValue = useCallback(
    (next: T) => {
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch { /* quota */ }
      setValueState(next);
    },
    [key],
  );

  return [value, setValue];
}
