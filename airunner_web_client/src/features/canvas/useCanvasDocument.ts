import { useEffect, useRef, useState, useCallback } from "react";
import { getCanvasDocument, saveCanvasDocument } from "../../api/canvas";

interface UseCanvasDocumentOptions {
  documentString: string | null;
  onLoad: (json: string) => void;
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
 * Loads the document on mount and autosaves via a debounced effect.
 */
export function useCanvasDocument({
  documentString,
  onLoad,
  isDirty,
  onSaved,
}: UseCanvasDocumentOptions): UseCanvasDocumentReturn {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadedRef = useRef(false);

  // Load the document on mount
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

  // Autosave via debounced effect
  useEffect(() => {
    if (!isLoaded || !isDirty) return;

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
    }, 1500);

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [documentString, isDirty, isLoaded]);

  // Manual save
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
