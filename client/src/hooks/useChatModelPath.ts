import { useRef, useCallback, useEffect } from "react";
import { getSingleton } from "../api/client";

export function useChatModelPath() {
  const modelPathRef = useRef("");

  const loadModelPath = useCallback(() => {
    getSingleton("LLMGeneratorSettings")
      .then((r) => {
        modelPathRef.current = String(r.model_path ?? "");
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadModelPath();
    const handler = () => loadModelPath();
    window.addEventListener("model-settings-changed", handler);
    return () => window.removeEventListener("model-settings-changed", handler);
  }, [loadModelPath]);

  return { modelPathRef };
}
