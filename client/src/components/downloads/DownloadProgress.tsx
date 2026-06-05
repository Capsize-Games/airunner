import { useState, useEffect, useRef } from "react";
import ProgressBar from "react-bootstrap/ProgressBar";
import { BASE_URL } from "../../types/api";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_DOWNLOADS } from "../../features/events/types";

interface DownloadState {
  progress: number;
  status: string;
  error?: string;
}

/**
 * Hook that subscribes to the SSE download-progress stream for one job.
 * First checks job existence via GET /status/{jobId} — if 404, calls
 * `onNotFound`.  Handles "interrupted" status (server restart).
 */
export function useDownloadProgress(
  jobId: string | null,
  onNotFound?: () => void,
): DownloadState {
  const [state, setState] = useState<DownloadState>({
    progress: 0,
    status: "pending",
  });
  const checkedRef = useRef(false);
  const onNotFoundRef = useRef(onNotFound);
  onNotFoundRef.current = onNotFound;

  // Initial check: fetch job status from HTTP endpoint
  useEffect(() => {
    if (!jobId || checkedRef.current) return;
    checkedRef.current = true;

    let cancelled = false;

    fetch(`${BASE_URL}/api/v1/downloads/status/${jobId}`)
      .then((res) => {
        if (cancelled) return;
        if (!res.ok) {
          setState({
            progress: 0, status: "failed",
            error: "Server restarted",
          });
          if (onNotFoundRef.current) onNotFoundRef.current();
          return null;
        }
        return res.json();
      })
      .then((job) => {
        if (!job || cancelled) return;

        if (job.status === "completed") {
          setState({ progress: 100, status: "completed" });
          return;
        }
        if (job.status === "failed") {
          setState({
            progress: 0, status: "failed",
            error: job.error ?? "Download failed",
          });
          return;
        }
        if (job.status === "cancelled") {
          setState({ progress: 0, status: "cancelled" });
          return;
        }
        if (job.status === "interrupted") {
          setState({
            progress: Number(job.progress) || 0, status: "interrupted",
            error: "Server was restarted",
          });
          return;
        }

        // Job exists and is running — apply initial progress
        setState({
          progress: Number(job.progress) || 0,
          status: "running",
        });
      })
      .catch(() => {
        if (!cancelled) {
          setState({
            progress: 0, status: "failed",
            error: "Could not check job status",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  // Subscribe to live download progress events via unified event bus
  useEventBus([EVENT_DOWNLOADS], (_event, data) => {
    if (!jobId) return;
    const payload = data as {
      job_id?: string;
      type?: string;
      progress?: number;
      status?: string;
      error?: string;
    };
    if (payload.job_id !== jobId) return;

    if (payload.type === "progress") {
      setState({
        progress: Number(payload.progress) || 0,
        status: payload.status ?? "running",
      });
    } else if (payload.type === "completed") {
      setState({ progress: 100, status: "completed" });
    } else if (payload.type === "error") {
      setState((prev) => ({
        ...prev,
        status: "failed",
        error: payload.error ?? "Download failed",
      }));
    } else if (payload.type === "cancelled") {
      setState((prev) => ({ ...prev, status: "cancelled" }));
    }
  });

  return state;
}

interface DownloadProgressProps {
  jobId: string;
  label?: string;
  onNotFound?: () => void;
}

/**
 * Compact inline progress bar for an active download.
 */
export default function DownloadProgress({
  jobId,
  label,
  onNotFound,
}: DownloadProgressProps) {
  const state = useDownloadProgress(jobId, onNotFound);

  const isRunning = state.status === "running";
  const isDone = state.status === "completed";
  const isFailed = state.status === "failed";
  const isCancelled = state.status === "cancelled";
  const isInterrupted = state.status === "interrupted";

  const variant = isDone
    ? "success"
    : isFailed
      ? "danger"
      : "info";

  return (
    <div style={{ fontSize: 11 }}>
      {label && (
        <div
          className="text-muted text-truncate mb-1"
          style={{ maxWidth: "100%" }}
        >
          {label}
        </div>
      )}
      <ProgressBar
        now={Math.min(state.progress, 100)}
        animated={isRunning}
        variant={variant}
        style={{ height: 6 }}
      />
      <div
        className="d-flex justify-content-between mt-1"
        style={{ fontSize: 10, color: "#888" }}
      >
        <span>
          {isDone
            ? "Complete"
            : isFailed
              ? "Failed"
              : isCancelled
                ? "Cancelled"
                : isInterrupted
                  ? "Interrupted"
                  : `${Math.round(state.progress)}%`}
        </span>
        <span style={{ display: "flex", gap: 4, alignItems: "center" }}>
          {state.error && !isInterrupted && (
            <span style={{ color: "var(--bs-danger)" }}>
              {state.error}
            </span>
          )}
        </span>
      </div>
    </div>
  );
}
