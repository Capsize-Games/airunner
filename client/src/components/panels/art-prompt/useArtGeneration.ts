import { useState, useRef, useCallback } from "react";
import {
  startArtGeneration,
  getArtJobStatus,
} from "../../../api/client";
import type { ArtJobStatus } from "../../../types/api";

export function useArtGeneration() {
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const jobIdRef = useRef<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleCancel = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    jobIdRef.current = null;
    setGenerating(false);
    setProgress(0);
  }, []);

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
      if (generating || !prompt.trim()) return;
      setGenerating(true);
      setProgress(0);
      try {
        const resp = await startArtGeneration({
          prompt: prompt.trim(),
          negative_prompt: negativePrompt?.trim() || undefined,
          model: artModel || undefined,
          version: artVersion || undefined,
          scheduler: scheduler || undefined,
          num_images: 1,
          width: width ?? undefined,
          height: height ?? undefined,
        });
        jobIdRef.current = resp.job_id;
        pollRef.current = setInterval(async () => {
          try {
            const status: ArtJobStatus = await getArtJobStatus(
              resp.job_id,
            );
            setProgress(status.progress ?? 0);
            if (
              status.status === "complete" ||
              status.status === "completed"
            ) {
              if (status.image && onComplete) {
                onComplete(status.image);
              }
              handleCancel();
            } else if (status.status === "failed") {
              handleCancel();
            }
          } catch {
            // keep polling
          }
        }, 1000);
      } catch {
        setGenerating(false);
      }
    },
    [generating, handleCancel],
  );

  return {
    generating,
    progress,
    handleSubmit,
    handleCancel,
  };
}
