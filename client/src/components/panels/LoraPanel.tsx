import { useState, useRef, useEffect } from "react";
import Spinner from "react-bootstrap/Spinner";
import type { LoraInfo } from "../../api/client";
import LoraItem from "./lora/LoraItem";
import { useEventBus } from "../../features/events/useEventBus";
import { EVENT_LORAS } from "../../features/events/types";
import { useLoras } from "../../hooks/useLoras";

interface LoraItemData extends LoraInfo {
  _inputText: string;
}

/** Variant versions whose LoRAs are stored under the SDXL 1.0 directory. */
const VARIANT_BASE: Record<string, string> = {
  "SDXL Lightning": "SDXL 1.0",
  "SDXL Hyper": "SDXL 1.0",
};

function getVersion(): string {
  try { return localStorage.getItem("airunner_art_version") || ""; }
  catch { return ""; }
}

export default function LoraPanel() {
  const { loras, loading, sync, patchLora } = useLoras();
  const [inputTexts, setInputTexts] = useState<Record<number, string>>({});
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const copiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Filter by selected art version.
  const version = getVersion();
  const baseDir = VARIANT_BASE[version] || version;
  const items: LoraItemData[] = loras
    .filter((l) => version ? (l.path || "").includes(`/${baseDir}/`) : true)
    .map((l) => ({ ...l, _inputText: inputTexts[l.id] ?? "" }));

  // Sync on EVENT_LORAS instead of full reload.
  useEventBus([EVENT_LORAS], (_event, data) => {
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
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, { enabled });
      await patchLora(updated);
      window.dispatchEvent(new CustomEvent("lora-changed", { detail: { id, enabled: updated.enabled } }));
    } catch { /* */ }
  };

  const handleWeightChange = async (id: number, weight: number) => {
    try {
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, { weight });
      await patchLora(updated);
      window.dispatchEvent(new CustomEvent("lora-changed", { detail: { id, weight: updated.weight } }));
    } catch { /* */ }
  };

  const handleCopyWord = (word: string) => {
    navigator.clipboard.writeText(word).catch(() => {});
    setCopiedIndex(word);
    if (copiedTimer.current) clearTimeout(copiedTimer.current);
    copiedTimer.current = setTimeout(() => setCopiedIndex(null), 1500);
  };

  const handleDeleteWord = async (id: number, word: string) => {
    const item = loras.find((i) => i.id === id);
    if (!item) return;
    const remaining = item.trigger_words.filter((w) => w !== word);
    try {
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, { trigger_words: remaining.join(",") });
      await patchLora(updated);
    } catch { /* */ }
  };

  const handleAddWords = async (id: number) => {
    const item = loras.find((i) => i.id === id);
    const text = inputTexts[id] ?? "";
    if (!item || !text.trim()) return;
    const newWords = text.split(",")
      .map((w) => w.trim())
      .filter((w) => w.length > 0 && !item.trigger_words.includes(w));
    if (newWords.length === 0) return;
    const merged = [...item.trigger_words, ...newWords];
    try {
      const { updateLora } = await import("../../api/client");
      const updated = await updateLora(id, { trigger_words: merged.join(",") });
      await patchLora(updated);
      setInputTexts((prev) => ({ ...prev, [id]: "" }));
    } catch { /* */ }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent, id: number) => {
    if (e.key === "Enter") { e.preventDefault(); handleAddWords(id); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <div style={{
        position: "sticky", top: 0,
        flexShrink: 0,
        display: "flex", alignItems: "center",
        padding: "8px 12px 6px",
        borderBottom: "1px solid var(--theme-border)",
        background: "var(--theme-panel-bg)",
        zIndex: 1,
      }}>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: "0.07em",
          textTransform: "uppercase", color: "var(--theme-text-secondary)",
        }}>
          LoRA
        </span>
      </div>
      <div className="p-2">
        {loading ? (
          <Spinner animation="border" size="sm" className="d-block mx-auto" />
        ) : items.length === 0 ? (
          <p className="text-muted small">
            No LoRA models found. Add .safetensors files to your models directory.
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
                  setInputTexts((prev) => ({ ...prev, [id]: value }))
                }
                onInputKeyDown={handleInputKeyDown}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
