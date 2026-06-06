import { useState, useRef, useCallback } from "react";
import { useArtWebSocket } from "../../../features/art/useArtWebSocket";

export function useArtGeneration() {
  const artWs = useArtWebSocket();

  const handleCancel = useCallback(() => {
    artWs.cancel();
  }, [artWs]);

  const handleSubmit = useCallback(
    async (params: {
      prompt: string;
      negativePrompt?: string;
      artModel?: string;
      artVersion?: string;
      scheduler?: string;
      width?: number;
      height?: number;
      onComplete?: (imageBase64: string) => void;
    }) => {
      const {
        prompt,
        negativePrompt,
        artModel,
        artVersion,
        scheduler,
        width,
        height,
        onComplete,
      } = params;
      if (artWs.generating || !prompt.trim()) return;

      try {
        const image = await artWs.generate({
          prompt: prompt.trim(),
          negativePrompt,
          artModel,
          artVersion,
          scheduler,
          width,
          height,
        });
        if (onComplete && image) {
          onComplete(image);
        }
      } catch {
        // cancelled or failed — handled by artWs state
      }
    },
    [artWs],
  );

  return {
    generating: artWs.generating,
    progress: artWs.progress,
    handleSubmit,
    handleCancel,
  };
}
