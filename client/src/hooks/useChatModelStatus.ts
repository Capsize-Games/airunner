import { useState, useEffect, useCallback } from "react";
import { listActiveModels } from "../api/client";
import type { ActiveModelInfo } from "../api/client";
import { useEventBus } from "../features/events/useEventBus";
import { EVENT_MODEL_STATUS } from "../features/events/types";

export function useChatModelStatus() {
  const [modelStatus, setModelStatus] = useState<string>("unloaded");

  const fetchStatus = useCallback(async () => {
    try {
      const resp = await listActiveModels();
      const llm = resp.models.find(
        (m: ActiveModelInfo) => m.model_type.toLowerCase() === "llm",
      );
      setModelStatus(llm?.status ?? "unloaded");
    } catch {
      // endpoint may be unavailable
    }
  }, []);

  // Fetch once for the initial state, then rely on the server's pushed
  // `model_status` events instead of polling /api/v1/models/active.
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEventBus([EVENT_MODEL_STATUS], () => {
    fetchStatus();
  });

  return {
    modelStatus,
    isModelLoading: modelStatus === "loading",
  };
}
