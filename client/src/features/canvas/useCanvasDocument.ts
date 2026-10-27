import { useEffect, useRef, useState, useCallback } from "react";
import { getCanvasDocument, saveCanvasDocument } from "../../api/canvas";
import { getRequestHeaders } from "virtual:extensions";

interface UseCanvasDocumentOptions {
  documentString: string | null;
  onLoad: (json: string) => void;
  /** Optional WebSocket send function for instant sync. */
  wsSend?: (document: string) => void;
  isDirty: boolean;
  onSaved?: () => void;
}

interface UseCanvasDocumentReturn {
  isLoaded: boolean;
  isSaving: boolean;
  saveError: string | null;
  save: () => Promise<void>;
}

/**
 * Hook that handles loading and saving the canvas document to the backend.
 *
 * Loading: fetches the document from the backend on mount (HTTP GET).
 * Saving:
 *  - When `wsSend` is provided, every dirty change is sent *immediately*
 *    through the WebSocket (no debounce).
 *  - HTTP PUT save also runs as a reliability fallback (debounced 500ms),
 *    ensuring data eventually reaches the server even if the WebSocket
 *    connection drops.
 *  - On `beforeunload` (page reload/close), sends the latest state via
 *    `navigator.sendBeacon` so data is not lost even on instant reload.
 *  - Also provides a manual `save()` for explicit save buttons.
 */
export function useCanvasDocument({
  documentString,
  onLoad,
  wsSend,
  isDirty,
  onSaved,
}: UseCanvasDocumentOptions): UseCanvasDocumentReturn {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadedRef = useRef(false);

  // Save the latest document string on page reload / close via
  // fetch with keepalive.  This is the only mechanism that guarantees
  // delivery during unload — neither WebSocket nor regular fetch survive
  // page teardown.
  const latestDocRef = useRef<string | null>(null);
  latestDocRef.current = documentString;
  useEffect(() => {
    const handler = () => {
      const doc = latestDocRef.current;
      if (!doc) return;
      try {
        fetch("/api/v1/canvas/document", {
          method: "PUT",
          headers: { "Content-Type": "application/json", ...getRequestHeaders() },
          body: JSON.stringify({ document: doc }),
          keepalive: true,
        });
      } catch {
        // Best-effort — swallow any errors during unload.
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  // Load the document on mount via HTTP GET (one-time).
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    const load = async () => {
      try {
        const data = await getCanvasDocument();
        if (data.document) {
          onLoad(data.document);
        }
      } catch {
        // Silently fail on autoload
      } finally {
        setIsLoaded(true);
      }
    };

    load();
  }, [onLoad]);

  // WebSocket path: send immediately on every dirty change.
  useEffect(() => {
    if (!isLoaded || !isDirty || !wsSend || !documentString) return;
    wsSend(documentString);
  }, [documentString, isDirty, isLoaded, wsSend]);

  // HTTP PUT reliability fallback — always active, debounced 500ms.
  // This ensures the server always has the latest state even if the
  // WebSocket connection drops or a message is lost.
  useEffect(() => {
    if (!isLoaded || !isDirty || !documentString) return;

    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    debounceTimer.current = setTimeout(async () => {
      if (!documentString) return;
      try {
        setSaveError(null);
        await saveCanvasDocument(documentString);
        onSaved?.();
      } catch {
        // Silently fail on autosave errors
      }
    }, 500);

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [documentString, isDirty, isLoaded, onSaved]);

  // Manual save (always uses HTTP PUT).
  const save = useCallback(async () => {
    if (!documentString) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await saveCanvasDocument(documentString);
      onSaved?.();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to save canvas";
      setSaveError(msg);
    } finally {
      setIsSaving(false);
    }
  }, [documentString]);

  return { isLoaded, isSaving, saveError, save };
}
