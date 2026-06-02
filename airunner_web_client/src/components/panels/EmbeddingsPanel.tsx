import { useState, useEffect, useCallback, useRef } from "react";
import Spinner from "react-bootstrap/Spinner";
import Form from "react-bootstrap/Form";
import type { EmbeddingInfo } from "../../api/client";
import { BASE_URL } from "../../types/api";

interface EmbeddingItem extends EmbeddingInfo {
  _inputText: string;
}

export default function EmbeddingsPanel() {
  const [items, setItems] = useState<EmbeddingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const { listEmbeddings } = await import("../../api/client");
      const data = await listEmbeddings();
      const version = (() => {
        try { return localStorage.getItem("airunner_art_version") || ""; }
        catch { return ""; }
      })();
      const filtered = data.embeddings.filter((e: EmbeddingInfo) =>
        version ? e.path.includes(`/${version}/`) : true,
      );
      setItems(
        filtered.map((e: EmbeddingInfo) => ({
          ...e,
          _inputText: "",
        })),
      );
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load on mount
  useEffect(() => {
    reload();
  }, [reload]);

  // Re-filter when version changes
  useEffect(() => {
    const handler = () => reload();
    window.addEventListener("art-version-changed", handler);
    return () => window.removeEventListener("art-version-changed", handler);
  }, [reload]);

  // Subscribe to SSE reload events
  useEffect(() => {
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/art/embeddings/watch`,
    );
    eventSource.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "reload") {
          reload();
        }
      } catch { /* ignore malformed events */ }
    });
    eventSource.onerror = () => {
      // The browser will automatically reconnect EventSource on error
    };
    return () => {
      eventSource.close();
    };
  }, [reload]);

  // Update individual items in-place when another component toggles
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as
        { id: number; enabled: boolean } | undefined;
      if (detail && detail.id) {
        setItems((prev) =>
          prev.map((item) =>
            item.id === detail.id
              ? { ...item, enabled: detail.enabled }
              : item,
          ),
        );
      }
    };
    window.addEventListener("embedding-changed", handler);
    return () =>
      window.removeEventListener("embedding-changed", handler);
  }, []);

  const handleToggle = async (id: number, enabled: boolean) => {
    try {
      const { updateEmbedding } = await import("../../api/client");
      await updateEmbedding(id, { enabled });
      setItems((prev) =>
        prev.map((item) =>
          item.id === id
            ? { ...item, enabled }
            : item,
        ),
      );
      window.dispatchEvent(
        new CustomEvent("embedding-changed", {
          detail: { id, enabled },
        }),
      );
    } catch { /* */ }
  };

  const handleCopyWord = (word: string) => {
    navigator.clipboard.writeText(word).catch(() => {});
    setCopiedIndex(word);
    if (copiedTimer.current) clearTimeout(copiedTimer.current);
    copiedTimer.current = setTimeout(() => setCopiedIndex(null), 1500);
  };

  const handleDeleteWord = async (id: number, word: string) => {
    const item = items.find((i) => i.id === id);
    if (!item) return;
    const remaining = item.trigger_words.filter((w) => w !== word);
    try {
      const { updateEmbedding } = await import("../../api/client");
      await updateEmbedding(id, {
        trigger_words: remaining.join(","),
      });
      setItems((prev) =>
        prev.map((i) =>
          i.id === id
            ? { ...i, trigger_words: remaining }
            : i,
        ),
      );
    } catch { /* */ }
  };

  const handleAddWords = async (id: number) => {
    const item = items.find((i) => i.id === id);
    if (!item || !item._inputText.trim()) return;
    const newWords = item._inputText
      .split(",")
      .map((w) => w.trim())
      .filter((w) => w.length > 0 && !item.trigger_words.includes(w));
    if (newWords.length === 0) return;
    const merged = [...item.trigger_words, ...newWords];
    try {
      const { updateEmbedding } = await import("../../api/client");
      await updateEmbedding(id, {
        trigger_words: merged.join(","),
      });
      setItems((prev) =>
        prev.map((i) =>
          i.id === id
            ? { ...i, trigger_words: merged, _inputText: "" }
            : i,
        ),
      );
    } catch { /* */ }
  };

  const handleInputKeyDown = (
    e: React.KeyboardEvent,
    id: number,
  ) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddWords(id);
    }
  };

  return (
    <div className="p-2">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h6 className="text-muted mb-0">Embeddings</h6>
      </div>

      {loading ? (
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      ) : items.length === 0 ? (
        <p className="text-muted small">
          No textual inversion embeddings found. Add embedding files to
          your models directory and they will be detected automatically.
        </p>
      ) : (
        <div className="embed-list">
          {items.map((item) => (
            <div
              key={item.id}
              className="mb-3 p-2 rounded"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid #333",
              }}
            >
              {/* Header: checkbox + name */}
              <div className="d-flex align-items-center gap-2 mb-1">
                <Form.Check
                  type="switch"
                  checked={item.enabled}
                  onChange={(e) => handleToggle(item.id, e.target.checked)}
                  id={`embed-enable-${item.id}`}
                />
                <span
                  className="small"
                  style={{
                    color: item.enabled ? "#c8c8c8" : "#666",
                  }}
                >
                  {item.name}
                </span>
              </div>

              {/* Trigger words — pills */}
              {item.trigger_words.length > 0 && (
                <div className="d-flex flex-wrap gap-1 mb-1">
                  {item.trigger_words.map((word) => (
                    <span
                      key={word}
                      onClick={() => handleCopyWord(word)}
                      title="Click to copy"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 3,
                        background:
                          copiedIndex === word
                            ? "rgba(0,185,0,0.2)"
                            : "rgba(0,132,185,0.15)",
                        border:
                          copiedIndex === word
                            ? "1px solid #00a800"
                            : "1px solid var(--bs-primary)",
                        borderRadius: 10,
                        padding: "2px 8px",
                        fontSize: "0.75rem",
                        color: "var(--theme-text)",
                        cursor: "pointer",
                      }}
                    >
                      <span
                        style={{
                          cursor: "pointer",
                          color: "#ff5555",
                          fontSize: "0.85rem",
                          lineHeight: 1,
                          padding: "1px 2px",
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteWord(item.id, word);
                        }}
                        title="Remove trigger word"
                      >
                        ✕
                      </span>
                      {copiedIndex === word ? "Copied!" : word}
                    </span>
                  ))}
                </div>
              )}

              {/* Add trigger words input */}
              <div className="d-flex gap-1">
                <Form.Control
                  size="sm"
                  type="text"
                  placeholder="Add trigger words (comma-separated)..."
                  value={item._inputText}
                  onChange={(e) =>
                    setItems((prev) =>
                      prev.map((i) =>
                        i.id === item.id
                          ? { ...i, _inputText: e.target.value }
                          : i,
                      ),
                    )
                  }
                  onKeyDown={(e) => handleInputKeyDown(e, item.id)}
                  style={{
                    background: "#1a1a2e",
                    color: "var(--theme-text)",
                    borderColor: "#333",
                    fontSize: "0.7rem",
                  }}
                />
                <button
                  className="btn btn-sm"
                  onClick={() => handleAddWords(item.id)}
                  disabled={!item._inputText.trim()}
                  style={{
                    background: "var(--bs-primary)",
                    border: "none",
                    color: "#fff",
                    fontSize: "0.7rem",
                    padding: "2px 8px",
                  }}
                >
                  Add
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
