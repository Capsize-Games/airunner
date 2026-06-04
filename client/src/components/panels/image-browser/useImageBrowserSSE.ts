import { useEffect } from "react";
import { BASE_URL } from "../../../types/api";

export function useImageBrowserSSE(
  onReload: () => void,
) {
  useEffect(() => {
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/art/images/watch`,
    );
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "reload") {
          onReload();
        }
      } catch {
        // ignore malformed events
      }
    };
    eventSource.onerror = () => {
      // The browser will auto-reconnect
    };
    return () => {
      eventSource.close();
    };
  }, [onReload]);
}
