import { useEventBus } from "../../../features/events/useEventBus";
import { EVENT_IMAGES } from "../../../features/events/types";

export function useImageBrowserSSE(
  onReload: () => void,
) {
  useEventBus([EVENT_IMAGES], (_event, data) => {
    const payload = data as { type?: string };
    if (payload.type === "reload") {
      onReload();
    }
  });
}
