import { useState, useEffect } from "react";
import ProgressBar from "react-bootstrap/ProgressBar";
import { BASE_URL } from "../../types/api";

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

  useEffect(() => {
    if (!jobId) return;

    let eventSource: EventSource | null = null;
    let cancelled = false;

    fetch(`${BASE_URL}/api/v1/downloads/status/${jobId}`)
      .then((res) => {
        if (cancelled) return;
        if (!res.ok) {
          setState({
            progress: 0, status: "failed",
            error: "Server restarted",
          });
          if (onNotFound) onNotFound();
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

        // Job exists and is running — open SSE stream
        setState({ progress: Number(job.progress) || 0, status: "running" });

        eventSource = new EventSource(
          `${BASE_URL}/api/v1/downloads/status/${jobId}/stream`,
        );

        eventSource.addEventListener("message", (event) => {
          try {
            const data = JSON.parse(event.data);
            const type = data.type;

            if (type === "progress") {
              setState({
                progress: Number(data.progress) || 0,
                status: data.status ?? "running",
              });
            } else if (type === "complete") {
              setState({ progress: 100, status: "completed" });
              eventSource?.close();
            } else if (type === "error") {
              setState((prev) => ({
                ...prev,
                status: "failed",
                error: data.error ?? "Download failed",
              }));
              eventSource?.close();
            } else if (type === "cancelled") {
              setState((prev) => ({ ...prev, status: "cancelled" }));
              eventSource?.close();
            }
          } catch {
            // ignore parse errors
          }
        });

        eventSource.onerror = () => {
          // EventSource auto-reconnects
        };
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
      if (eventSource) eventSource.close();
    };
  }, [jobId, onNotFound]);

  return state;
}

interface DownloadProgressProps {
  jobId: string;
  label?: string;
  onNotFound?: () => void;
  onRetry?: () => void;
}

/**
 * Compact inline progress bar for an active download.
 */
export default function DownloadProgress({
  jobId,
  label,
  onNotFound,
  onRetry,
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
          {isInterrupted && onRetry && (
            <button
              onClick={onRetry}
              style={{
                background: "rgba(255,255,255,0.15)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: 3,
                color: "#ccc",
                cursor: "pointer",
                fontSize: 10,
                padding: "1px 6px",
              }}
            >
              Retry
            </button>
          )}
        </span>
      </div>
    </div>
  );
}
