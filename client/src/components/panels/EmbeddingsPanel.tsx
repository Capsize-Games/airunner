import { useState, useRef, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import type { EmbeddingInfo } from "../../api/client";
import EmbeddingItem from "./embeddings/EmbeddingItem";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_EMBEDDINGS } from "../../features/events/types";
import { useEmbeddings } from "../../hooks/useEmbeddings";

interface EmbeddingItemData extends EmbeddingInfo {
  _inputText: string;
}

/** Variant versions whose embeddings are stored under the SDXL 1.0 directory. */
const VARIANT_BASE: Record<string, string> = {
  "SDXL Lightning": "SDXL 1.0",
  "SDXL Hyper": "SDXL 1.0",
};

function getVersion(): string {
  try { return localStorage.getItem("airunner_art_version") || ""; }
  catch { return ""; }
}

export default function EmbeddingsPanel() {
  const { embeddings, loading, sync, patchEmbedding } = useEmbeddings();
  const [inputTexts, setInputTexts] = useState<Record<number, string>>({});
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const version = getVersion();
  const baseDir = VARIANT_BASE[version] || version;
  const items: EmbeddingItemData[] = embeddings
    .filter((e) => version ? (e.path || "").includes(`/${baseDir}/`) : true)
    .map((e) => ({ ...e, _inputText: inputTexts[e.id] ?? "" }));

  useEventBus([EVENT_EMBEDDINGS], (_event, data) => {
    const payload = data as { type?: string };
    if (payload.type === "reload") sync();
  });

  useEffect(() => {
    const handler = () => sync();
    window.addEventListener("art-version-changed", handler);
    return () => window.removeEventListener("art-version-changed", handler);
  }, [sync]);

  const handleToggle = async (id: number, enabled: boolean) => {
    try {
      const { updateEmbedding } = await import("../../api/client");
      const updated = await updateEmbedding(id, { enabled });
      await patchEmbedding(updated);
      window.dispatchEvent(new CustomEvent("embedding-changed", { detail: { id, enabled } }));
    } catch { /* */ }
  };

  const handleCopyWord = (word: string) => {
    navigator.clipboard.writeText(word).catch(() => {});
    setCopiedIndex(word);
    if (copiedTimer.current) clearTimeout(copiedTimer.current);
    copiedTimer.current = setTimeout(() => setCopiedIndex(null), 1500);
  };

  const handleDeleteWord = async (id: number, word: string) => {
    const item = embeddings.find((i) => i.id === id);
    if (!item) return;
    const remaining = item.trigger_words.filter((w) => w !== word);
    try {
      const { updateEmbedding } = await import("../../api/client");
      await updateEmbedding(id, { trigger_words: remaining.join(",") });
      await patchEmbedding({ ...item, trigger_words: remaining });
    } catch { /* */ }
  };

  const handleAddWords = async (id: number) => {
    const item = embeddings.find((i) => i.id === id);
    const text = inputTexts[id] ?? "";
    if (!item || !text.trim()) return;
    const newWords = text.split(",")
      .map((w) => w.trim())
      .filter((w) => w.length > 0 && !item.trigger_words.includes(w));
    if (newWords.length === 0) return;
    const merged = [...item.trigger_words, ...newWords];
    try {
      const { updateEmbedding } = await import("../../api/client");
      const updated = await updateEmbedding(id, { trigger_words: merged.join(",") });
      await patchEmbedding(updated);
      setInputTexts((prev) => ({ ...prev, [id]: "" }));
    } catch { /* */ }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent, id: number) => {
    if (e.key === "Enter") { e.preventDefault(); handleAddWords(id); }
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
                setInputTexts((prev) => ({ ...prev, [id]: value }))
              }
              onInputKeyDown={handleInputKeyDown}
            />
          ))}
        </div>
      )}
    </div>
  );
}
