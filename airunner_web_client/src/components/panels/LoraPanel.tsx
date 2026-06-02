import { useState, useEffect, useCallback, useRef } from "react";
import Spinner from "react-bootstrap/Spinner";
import type { LoraInfo } from "../../api/client";
import { BASE_URL } from "../../types/api";
import LoraItem from "./lora/LoraItem";

interface LoraItemData extends LoraInfo {
  _inputText: string;
}

export default function LoraPanel() {
  const [items, setItems] = useState<LoraItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadLoras = useCallback(async () => {
    setLoading(true);
    try {
      const { listLoras } = await import("../../api/client");
      const data = await listLoras();
      const version = (() => {
        try { return localStorage.getItem("airunner_art_version") || ""; }
        catch { return ""; }
      })();
      const filtered = data.loras.filter((l: LoraInfo) =>
        version ? l.path.includes(`/${version}/`) : true,
      );
      setItems(
        filtered.map((l: LoraInfo) => ({
          ...l,
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
    loadLoras();
  }, [loadLoras]);

  useEffect(() => {
    const handler = () => loadLoras();
    window.addEventListener("art-version-changed", handler);
    return () => window.removeEventListener("art-version-changed", handler);
  }, [loadLoras]);

  useEffect(() => {
    const eventSource = new EventSource(
      `${BASE_URL}/api/v1/art/loras/watch`,
    );
    eventSource.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "reload") {
          loadLoras();
        }
      } catch { /* ignore malformed events */ }
    });
    eventSource.onerror = () => {
      // The browser will automatically reconnect EventSource on error
    };
    return () => {
      eventSource.close();
    };
  }, [loadLoras]);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as { id: number; enabled: boolean } | undefined;
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
    window.addEventListener("lora-changed", handler);
    return () => window.removeEventListener("lora-changed", handler);
  }, []);

  const handleToggle = async (id: number, enabled: boolean) => {
    try {
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, { enabled });
      setItems((prev) =>
        prev.map((item) =>
          item.id === id
            ? { ...item, enabled: updated.enabled }
            : item,
        ),
      );
      window.dispatchEvent(
        new CustomEvent("lora-changed", {
          detail: { id, enabled: updated.enabled },
        }),
      );
    } catch { /* */ }
  };

  const handleWeightChange = async (id: number, weight: number) => {
    try {
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, { weight });
      setItems((prev) =>
        prev.map((item) =>
          item.id === id
            ? { ...item, weight: updated.weight }
            : item,
        ),
      );
      window.dispatchEvent(
        new CustomEvent("lora-changed", {
          detail: { id, weight: updated.weight },
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
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, {
        trigger_words: remaining.join(","),
      });
      setItems((prev) =>
        prev.map((i) =>
          i.id === id
            ? { ...i, trigger_words: updated.trigger_words }
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
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, {
        trigger_words: merged.join(","),
      });
      setItems((prev) =>
        prev.map((i) =>
          i.id === id
            ? { ...i, trigger_words: updated.trigger_words, _inputText: "" }
            : i,
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
        <h6 className="text-muted mb-0">LoRA</h6>
      </div>

      {loading ? (
        <Spinner animation="border" size="sm" className="d-block mx-auto" />
      ) : items.length === 0 ? (
        <p className="text-muted small">
          No LoRA models found. Add .safetensors files to
          your models directory.
        </p>
      ) : (
        <div className="lora-list">
          {items.map((item) => (
            <LoraItem
              key={item.id}
              item={item}
              onToggle={handleToggle}
              onWeightChange={handleWeightChange}
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
