import { useState, useEffect, useCallback, useRef } from "react";
import Spinner from "react-bootstrap/Spinner";
import type { EmbeddingInfo } from "../../api/client";
import { BASE_URL } from "../../types/api";
import EmbeddingItem from "./embeddings/EmbeddingItem";

interface EmbeddingItemData extends EmbeddingInfo {
  _inputText: string;
}

export default function EmbeddingsPanel() {
  const [items, setItems] = useState<EmbeddingItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Variant versions whose LoRAs/embeddings are stored under the
   *  SDXL 1.0 directory rather than their own version directory. */
  const VARIANT_BASE: Record<string, string> = {
    "SDXL Lightning": "SDXL 1.0",
    "SDXL Hyper": "SDXL 1.0",
  };

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const { listEmbeddings } = await import("../../api/client");
      const data = await listEmbeddings();
      const version = (() => {
        try { return localStorage.getItem("airunner_art_version") || ""; }
        catch { return ""; }
      })();
      const baseDir = VARIANT_BASE[version] || version;
      const filtered = data.embeddings.filter((e: EmbeddingInfo) =>
        version ? e.path.includes(`/${baseDir}/`) : true,
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

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    const handler = () => reload();
    window.addEventListener("art-version-changed", handler);
    return () => window.removeEventListener("art-version-changed", handler);
  }, [reload]);

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
          item.id === id ? { ...item, enabled } : item,
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
          i.id === id ? { ...i, trigger_words: remaining } : i,
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
          i.id === id ? { ...i, trigger_words: merged, _inputText: "" } : i,
        ),
      );
    } catch { /* */ }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent, id: number) => {
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
            <EmbeddingItem
              key={item.id}
              item={item}
              onToggle={handleToggle}
              onCopyWord={handleCopyWord}
              onDeleteWord={handleDeleteWord}
              onAddWords={handleAddWords}
              onInputChange={(id, value) =>
                setItems((prev) =>
                  prev.map((i) =>
                    i.id === id ? { ...i, _inputText: value } : i,
                  ),
                )
              }
              onInputKeyDown={handleInputKeyDown}
            />
          ))}
        </div>
      )}
    </div>
  );
}
