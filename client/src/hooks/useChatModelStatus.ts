import { useState, useEffect } from "react";
import { listActiveModels } from "../api/client";
import type { ActiveModelInfo } from "../api/client";

export function useChatModelStatus() {
  const [modelStatus, setModelStatus] = useState<string>("unloaded");

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const resp = await listActiveModels();
        const llm = resp.models.find(
          (m: ActiveModelInfo) => m.model_type.toLowerCase() === "llm",
        );
        setModelStatus(llm?.status ?? "unloaded");
      } catch {
        // endpoint may be unavailable
      }
    };
    fetchStatus();
    const id = setInterval(fetchStatus, 300);
    return () => clearInterval(id);
  }, []);

  return {
    modelStatus,
    isModelLoading: modelStatus === "loading",
  };
}
