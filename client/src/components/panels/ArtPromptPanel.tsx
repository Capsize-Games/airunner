import { Fragment, useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { saveToStorage } from "./art-model/ArtModelStorage";
import SavedPromptsPanel from "./art-prompt/SavedPromptsModal";
import LucideIcon from "../shared/LucideIcon";
import { PromptTextareas } from "./art-prompt/PromptTextareas";
import { PromptControls } from "./art-prompt/PromptControls";
import { ToolbarIconBtn } from "./art-prompt/ArtShared";
import { ArtDropdownPicker } from "./art-prompt/ArtDropdownPicker";
import { SettingsPopup } from "./art-prompt/SettingsPopup";
import LoraPanel from "./LoraPanel";
import EmbeddingsPanel from "./EmbeddingsPanel";
import { useArtPromptState } from "./art-prompt/useArtPromptState";

// side-effect: injects CSS for sliders / number spinners
import "./art-prompt/ArtShared";

function InlineNumberInput({ value, min, max, step, float, onChange, onClose }: {
  value: number; min: number; max: number; step?: number; float?: boolean; onChange: (v: number) => void; onClose: () => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      <input
        type="number" className="art-no-spin"
        defaultValue={value}
        onBlur={(e) => { const v = float ? parseFloat(e.target.value) : parseInt(e.target.value, 10); if (!isNaN(v) && v >= min && v <= max) { onChange(v); onClose(); } }}
        onKeyDown={(e) => { if (e.key === "Enter") { const v = float ? parseFloat((e.target as HTMLInputElement).value) : parseInt((e.target as HTMLInputElement).value, 10); if (!isNaN(v) && v >= min && v <= max) { onChange(v); onClose(); } } }}
        style={{ height: 22, width: 56, background: "var(--theme-input-bg)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "var(--theme-text)", fontSize: 10, textAlign: "center", padding: "0 4px" }}
        autoFocus
      />
      <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", opacity: 0.4 }}>({float ? `${min.toFixed(1)}–${max.toFixed(1)}` : `${min}–${max}`})</span>
    </div>
  );
}

function InlineOptionBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: "2px 8px", fontSize: 10, borderRadius: 4,
        border: "1px solid rgba(255,255,255,0.12)",
        background: active ? "rgba(var(--theme-primary-rgb), 0.15)" : "transparent",
        color: active ? "var(--bs-primary)" : "var(--theme-text-secondary)",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => { if (!active) (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)"; }}
      onMouseLeave={(e) => { if (!active) (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
    >
      {children}
    </button>
  );
}

function InlineSizeEditor({ w, h, onWChange, onHChange, onClose }: {
  w: number; h: number; onWChange: (v: number) => void; onHChange: (v: number) => void; onClose: () => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 9, color: "var(--theme-text-secondary)" }}>W</span>
      <input type="number" className="art-no-spin" defaultValue={w}
        onBlur={(e) => { const v = Math.max(64, Math.min(2048, Number(e.target.value))); if (!isNaN(v)) onWChange(v); onClose(); }}
        onKeyDown={(e) => { if (e.key === "Enter") { const v = Math.max(64, Math.min(2048, Number((e.target as HTMLInputElement).value))); if (!isNaN(v)) { onWChange(v); onClose(); } } }}
        style={{ height: 22, width: 56, background: "var(--theme-input-bg)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "var(--theme-text)", fontSize: 10, textAlign: "center", padding: "0 4px" }} autoFocus />
      <span style={{ fontSize: 9, color: "var(--theme-text-secondary)" }}>H</span>
      <input type="number" className="art-no-spin" defaultValue={h}
        onBlur={(e) => { const v = Math.max(64, Math.min(2048, Number(e.target.value))); if (!isNaN(v)) onHChange(v); onClose(); }}
        onKeyDown={(e) => { if (e.key === "Enter") { const v = Math.max(64, Math.min(2048, Number((e.target as HTMLInputElement).value))); if (!isNaN(v)) { onHChange(v); onClose(); } } }}
        style={{ height: 22, width: 56, background: "var(--theme-input-bg)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "var(--theme-text)", fontSize: 10, textAlign: "center", padding: "0 4px" }} />
    </div>
  );
}

function InfoItem({ label, value, icon, editing, dimmed, onClick, children, editor }: {
  label: string;
  value?: string;
  icon?: string;
  editing?: boolean;
  dimmed?: boolean;
  onClick?: (e: React.MouseEvent) => void;
  children?: React.ReactNode;
  editor?: React.ReactNode;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "3px 10px",
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        cursor: onClick ? "pointer" : "default",
      }}
      onMouseEnter={(e) => { if (onClick) (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.03)"; }}
      onMouseLeave={(e) => { if (onClick) (e.currentTarget as HTMLDivElement).style.background = "transparent"; }}
    >
      {icon && <LucideIcon name={icon} size={10} />}
      <span style={{ color: "var(--theme-text-secondary)", opacity: 0.55, fontSize: 10, width: 80, flexShrink: 0 }}>{label}</span>
      {editing && editor ? (
        <div style={{ flex: 1, minWidth: 0 }} onClick={(e) => e.stopPropagation()}>{editor}</div>
      ) : value !== undefined ? (
        <span style={{ color: "var(--theme-text)", opacity: dimmed ? 0.35 : 1, fontSize: 10, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{value}</span>
      ) : null}
      {children}
    </div>
  );
}

export default function ArtPromptPanel({ visible = true }: { visible?: boolean }) {
  const s = useArtPromptState();

  const [showModelOptions, setShowModelOptions] = useState(false);
  const modelOptionsBtnRef = useRef<HTMLDivElement>(null);
  const [modelOptionsAnchor, setModelOptionsAnchor] = useState<{ left: number; bottom: number } | null>(null);

  // ── Size picker ──
  const sizePortalId = useRef(`size-portal-${Math.random().toString(36).slice(2, 8)}`).current;
  const [showSize, setShowSize] = useState(false);
  const sizeBtnRef = useRef<HTMLDivElement>(null);
  const [sizeAnchor, setSizeAnchor] = useState<{ left: number; bottom: number } | null>(null);
  const sizeEmittingRef = useRef(false);

  useEffect(() => {
    if (!showSize) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      const portalEl = document.getElementById(sizePortalId);
      if (portalEl?.contains(target)) return;
      if (sizeBtnRef.current && !sizeBtnRef.current.contains(target))
        setShowSize(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showSize, sizePortalId]);

  useEffect(() => {
    const handler = () => {
      if (sizeEmittingRef.current) return;
      setShowSize(false);
    };
    window.addEventListener("art-overlay-opened", handler);
    window.addEventListener("chat-picker-opened", handler);
    return () => {
      window.removeEventListener("art-overlay-opened", handler);
      window.removeEventListener("chat-picker-opened", handler);
    };
  }, []);

  const handleSizeToggle = () => {
    const next = !showSize;
    setShowSize(next);
    if (next) {
      sizeEmittingRef.current = true;
      window.dispatchEvent(new Event("art-overlay-opened"));
      sizeEmittingRef.current = false;
      if (sizeBtnRef.current) {
        const r = sizeBtnRef.current.getBoundingClientRect();
        setSizeAnchor({ left: r.left, bottom: window.innerHeight - r.top + 4 });
      }
    }
  };

  // Close model options on outside clicks
  useEffect(() => {
    if (!showModelOptions) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (modelOptionsBtnRef.current?.contains(target)) return;
      if (document.getElementById("art-model-options-popup")?.contains(target)) return;
      const dropdownPortals = document.querySelectorAll("[data-dropdown-portal]");
      for (const portal of dropdownPortals) {
        if (portal.contains(target)) return;
      }
      setShowModelOptions(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showModelOptions]);

  const [focusedField, setFocusedField] = useState<string | null>(null);
  const [dropdownField, setDropdownField] = useState<string | null>(null);
  const [dropdownAnchor, setDropdownAnchor] = useState<{ left: number; bottom: number; minWidth: number } | null>(null);
  const dropdownEmittingRef = useRef(false);

  useEffect(() => {
    if (!dropdownField) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (document.getElementById("art-info-dropdown-popup")?.contains(target)) return;
      const dropdownPortals = document.querySelectorAll("[data-dropdown-portal]");
      for (const portal of dropdownPortals) {
        if (portal.contains(target)) return;
      }
      setDropdownField(null);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownField]);

  useEffect(() => {
    const handler = () => {
      if (dropdownEmittingRef.current) return;
      setDropdownField(null);
    };
    window.addEventListener("art-overlay-opened", handler);
    return () => window.removeEventListener("art-overlay-opened", handler);
  }, []);

  const openDropdown = (field: string, anchorRect: DOMRect) => {
    dropdownEmittingRef.current = true;
    window.dispatchEvent(new Event("art-overlay-opened"));
    dropdownEmittingRef.current = false;
    setDropdownAnchor({
      left: anchorRect.left + 100,
      bottom: window.innerHeight - anchorRect.top + 4,
      minWidth: anchorRect.width - 100,
    });
    setDropdownField(field);
  };

  const [showInfo, setShowInfo] = useState(() => {
    try { return localStorage.getItem("airunner_show_gen_info") !== "false"; }
    catch { return true; }
  });
  useEffect(() => {
    try { localStorage.setItem("airunner_show_gen_info", String(showInfo)); } catch {}
  }, [showInfo]);
  const [seedCopied, setSeedCopied] = useState(false);

  const handleToggleModelOptions = () => {
    const next = !showModelOptions;
    setShowModelOptions(next);
    if (next && modelOptionsBtnRef.current) {
      const r = modelOptionsBtnRef.current.getBoundingClientRect();
      setModelOptionsAnchor({ left: r.left, bottom: window.innerHeight - r.top + 4 });
    }
  };

  // ── Generation type picker ──
  const [showGenType, setShowGenType] = useState(false);
  const genTypeBtnRef = useRef<HTMLDivElement>(null);
  const [genTypeAnchor, setGenTypeAnchor] = useState<{ left: number; bottom: number } | null>(null);
  const genTypeEmittingRef = useRef(false);

  useEffect(() => {
    if (!showGenType) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (genTypeBtnRef.current?.contains(target)) return;
      if (document.getElementById("art-gen-type-popup")?.contains(target)) return;
      setShowGenType(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showGenType]);

  useEffect(() => {
    const handler = () => {
      if (genTypeEmittingRef.current) return;
      setShowGenType(false);
    };
    window.addEventListener("art-overlay-opened", handler);
    return () => window.removeEventListener("art-overlay-opened", handler);
  }, []);

  const handleToggleGenType = () => {
    const next = !showGenType;
    setShowGenType(next);
    if (next) {
      genTypeEmittingRef.current = true;
      window.dispatchEvent(new Event("art-overlay-opened"));
      genTypeEmittingRef.current = false;
      if (genTypeBtnRef.current) {
        const r = genTypeBtnRef.current.getBoundingClientRect();
        setGenTypeAnchor({ left: r.left, bottom: window.innerHeight - r.top + 4 });
      }
    }
  };

  if (!visible) return null;

  return (
    <Fragment>
      <div className="flex-grow-1 d-flex flex-column overflow-hidden w-100">

        <div className="d-flex flex-column flex-grow-1 overflow-hidden">
          <div className="flex-grow-1 d-flex flex-column bg-theme-input overflow-hidden min-h-0" style={{ border: "none", borderRadius: 0 }}>
            <PromptTextareas
              prompt={s.prompt}
              secondaryPrompt={s.secondaryPrompt}
              negativePrompt={s.negativePrompt}
              secondaryNegativePrompt={s.secondaryNegativePrompt}
              isMultiPrompt={s.isMultiPrompt}
              generating={s.generating}
              onPromptChange={(v) => { s.setPrompt(v); s.persist({ prompt: v }); }}
              onSecondaryPromptChange={(v) => { s.setSecondaryPrompt(v); s.persist({ secondary_prompt: v }); }}
              onNegativePromptChange={(v) => { s.setNegativePrompt(v); s.persist({ negative_prompt: v }); }}
              onSecondaryNegativePromptChange={(v) => { s.setSecondaryNegativePrompt(v); s.persist({ secondary_negative_prompt: v }); }}
            />

            {/* ── Info panel ── */}
            <div style={{
              borderTop: "1px solid rgba(255,255,255,0.08)",
              flexShrink: 0,
            }}>
              <button
                type="button"
                onClick={() => setShowInfo((v) => !v)}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  width: "100%", padding: "4px 10px",
                  border: "none",
                  background: "rgba(255,255,255,0.04)",
                  color: "var(--theme-text-secondary)",
                  cursor: "pointer", fontSize: 9, fontWeight: 700,
                  letterSpacing: "0.07em", textTransform: "uppercase",
                  opacity: 0.6,
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
                  (e.currentTarget as HTMLButtonElement).style.opacity = "0.85";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.04)";
                  (e.currentTarget as HTMLButtonElement).style.opacity = "0.6";
                }}
              >
                <LucideIcon name={showInfo ? "chevron-down" : "chevron-right"} size={10} />
                <span>Generation Info</span>
              </button>
              {showInfo && (
                <div style={{
                  display: "flex", flexDirection: "column",
                }}>
                  <InfoItem icon="sparkles" label="Model Version" value={s.version || "—"}
                    onClick={(e) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); openDropdown("version", r); }}
                  />
                  <InfoItem icon="sparkles" label="Model" value={s.modelPath ? s.modelPath.split("/").pop()?.replace(/\.(gguf|bin|safetensors|pt|pth|ckpt|pkl|model)$/i, "") || s.modelPath : "—"}
                    onClick={(e) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); openDropdown("model", r); }}
                  />
                  <InfoItem icon="sparkles" label="Scheduler" value={s.scheduler || "—"}
                    onClick={(e) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); openDropdown("scheduler", r); }}
                  />
                  <InfoItem icon="settings-2" label="Steps" value={String(s.steps)}
                    editing={focusedField === "steps"}
                    onClick={() => setFocusedField(focusedField === "steps" ? null : "steps")}
                    editor={
                      <InlineNumberInput value={s.steps} min={1} max={150}
                        onChange={(v) => { s.setSteps(v); saveToStorage("steps", v); s.persistGen({ steps: v }); }}
                        onClose={() => setFocusedField(null)}
                      />
                    }
                  />
                  <InfoItem icon="settings-2" label="CFG" value={String(s.cfgScale)}
                    editing={focusedField === "cfg"}
                    onClick={() => setFocusedField(focusedField === "cfg" ? null : "cfg")}
                    editor={
                      <InlineNumberInput value={s.cfgScale} min={1} max={30} step={0.1} float
                        onChange={(v) => { s.setCfgScale(v); saveToStorage("cfg_scale", v); s.persistGen({ cfg_scale: v }); }}
                        onClose={() => setFocusedField(null)}
                      />
                    }
                  />
                  <InfoItem icon="settings-2" label="Samples" value={String(s.nSamples)}
                    editing={focusedField === "samples"}
                    onClick={() => setFocusedField(focusedField === "samples" ? null : "samples")}
                    editor={
                      <InlineNumberInput value={s.nSamples} min={1} max={1000}
                        onChange={(v) => { s.setNSamples(v); saveToStorage("n_samples", v); s.persistGen({ n_samples: v }); }}
                        onClose={() => setFocusedField(null)}
                      />
                    }
                  />
                  <InfoItem icon="settings-2" label="Batch" value={String(s.imagesPerBatch)}
                    editing={focusedField === "batch"}
                    onClick={() => setFocusedField(focusedField === "batch" ? null : "batch")}
                    editor={
                      <InlineNumberInput value={s.imagesPerBatch} min={1} max={6}
                        onChange={(v) => { s.setImagesPerBatch(v); saveToStorage("images_per_batch", v); s.persistGen({ images_per_batch: v }); }}
                        onClose={() => setFocusedField(null)}
                      />
                    }
                  />
                  <InfoItem icon="image-plus" label="Gen type" value={s.generationType === "txt2img" ? "Text-to-image" : "Image-to-image"}
                    onClick={(e) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); openDropdown("gentype", r); }}
                  />
                  <InfoItem icon="shuffle"
                    label={s.seedRandomized ? "Seed (random)" : "Seed (fixed)"}
                    dimmed={s.seedRandomized}
                    editing={focusedField === "seed"}
                    onClick={() => setFocusedField(focusedField === "seed" ? null : "seed")}
                    editor={
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <input
                          type="number" className="art-no-spin"
                          value={s.seed}
                          onChange={(e) => { const v = Number(e.target.value); if (!isNaN(v)) s.handleSeedChange(v); }}
                          style={{
                            height: 22, width: 80,
                            background: "var(--theme-input-bg)",
                            border: "1px solid rgba(255,255,255,0.12)",
                            borderRadius: 4, color: "var(--theme-text)",
                            fontSize: 10, textAlign: "center", padding: "0 4px",
                          }}
                        />
                      </div>
                    }
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 4, flex: 1, minWidth: 0 }}>
                      {focusedField !== "seed" && (
                        <span style={{ color: "var(--theme-text)", opacity: s.seedRandomized ? 0.35 : 1, fontSize: 10 }}>
                          {String(s.seed)}
                        </span>
                      )}
                      {focusedField !== "seed" && (
                        <button
                          type="button"
                          title={s.seedRandomized ? "Seed: switch to fixed" : "Seed: switch to random"}
                          onClick={(e) => { e.stopPropagation(); s.handleToggleRandom(); }}
                          style={{
                            display: "flex", alignItems: "center", justifyContent: "center",
                            width: 18, height: 18, padding: 0,
                            border: "none", cursor: "pointer", borderRadius: 3,
                            background: s.seedRandomized ? "rgba(var(--bs-primary-rgb), 0.15)" : "transparent",
                            color: s.seedRandomized ? "var(--bs-primary)" : "rgba(255,255,255,0.35)",
                            flexShrink: 0,
                          }}
                          onMouseEnter={(e) => {
                            if (!s.seedRandomized) {
                              (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)";
                              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!s.seedRandomized) {
                              (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.35)";
                              (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                            }
                          }}
                        >
                          <LucideIcon name="shuffle" size={10} />
                        </button>
                      )}
                      {focusedField !== "seed" && (
                        <button
                        type="button"
                        title={seedCopied ? "Copied!" : "Copy seed to clipboard"}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigator.clipboard.writeText(String(s.seed));
                          setSeedCopied(true);
                          setTimeout(() => setSeedCopied(false), 1500);
                        }}
                        style={{
                          display: "flex", alignItems: "center", justifyContent: "center",
                          width: 18, height: 18, padding: 0,
                          border: "none", background: "transparent",
                          cursor: "pointer", borderRadius: 3,
                          color: seedCopied ? "var(--bs-primary)" : "rgba(255,255,255,0.35)",
                          flexShrink: 0,
                        }}
                        onMouseEnter={(e) => {
                          if (!seedCopied) {
                            (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)";
                            (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!seedCopied) {
                            (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.35)";
                            (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                          }
                        }}
                      >
                        <LucideIcon name={seedCopied ? "check" : "copy"} size={10} />
                      </button>
                      )}
                    </div>
                  </InfoItem>
                  <InfoItem icon="ruler-dimension-line"
                    label="Size"
                    value={`${s.genWidth}×${s.genHeight}`}
                    editing={focusedField === "size"}
                    onClick={() => setFocusedField(focusedField === "size" ? null : "size")}
                    editor={
                      <InlineSizeEditor
                        w={s.genWidth} h={s.genHeight}
                        onWChange={(v) => { s.setGenWidth(v); saveToStorage("gen_width", v); s.persistGen({ width: v }); }}
                        onHChange={(v) => { s.setGenHeight(v); saveToStorage("gen_height", v); s.persistGen({ height: v }); }}
                        onClose={() => setFocusedField(null)}
                      />
                    }
                  />
                  <InfoItem icon="puzzle"
                    label="LoRA"
                    value={`${s.activeLoras.length} LoRA enabled`}
                    onClick={() => s.togglePanel("lora")}
                  />
                  <InfoItem icon="scan-text"
                    label="Embeddings"
                    value={s.isMultiPrompt
                      ? `${s.activeEmbeddings.length} Embeddings enabled`
                      : "Embeddings unavailable for Z-Image"
                    }
                    onClick={s.isMultiPrompt ? () => s.togglePanel("embeddings") : undefined}
                  />
                </div>
              )}
            </div>

            {!showInfo ? <div style={{
              display: "flex", alignItems: "center", gap: 4,
              padding: "2px 6px",
              borderTop: "1px solid rgba(255,255,255,0.08)",
              flexShrink: 0,
            }}>
              <div ref={modelOptionsBtnRef}>
                <ToolbarIconBtn
                  title="Art model options"
                  onClick={handleToggleModelOptions}
                  active={showModelOptions}
                >
                  <LucideIcon name="sparkles" size={14} />
                </ToolbarIconBtn>
              </div>
              {showModelOptions && modelOptionsAnchor && createPortal(
                <div
                  id="art-model-options-popup"
                  className="bg-theme-panel d-flex flex-column"
                  style={{
                    position: "fixed",
                    left: modelOptionsAnchor.left,
                    bottom: modelOptionsAnchor.bottom,
                    border: "1px solid rgba(255,255,255,0.14)",
                    borderRadius: 6,
                    zIndex: 1300,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                    minWidth: 220,
                    padding: "8px 0",
                    gap: 4,
                  }}
                >
                  <div style={{
                    fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
                    textTransform: "uppercase", color: "var(--theme-text-secondary)",
                    opacity: 0.6, padding: "4px 10px 2px",
                  }}>Art Model Options</div>

                  {/* Version */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "4px 10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 9, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--theme-text-secondary)", opacity: 0.6 }}>
                      <LucideIcon name="circle-dot" size={9} />
                      <span>Version</span>
                    </div>
                    <ArtDropdownPicker
                      value={s.version}
                      placeholder="Choose version…"
                      options={s.artOptions?.versions?.map((v) => ({ label: v.name, value: v.name })) ?? []}
                      onChange={s.handleVersion}
                    />
                  </div>

                  {/* Model */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "4px 10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 9, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--theme-text-secondary)", opacity: 0.6 }}>
                      <LucideIcon name="circle-dot" size={9} />
                      <span>Model</span>
                    </div>
                    <ArtDropdownPicker
                      value={s.modelPath}
                      placeholder="Choose model…"
                      options={s.artOptions?.versions?.find((v) => v.name === s.version)?.models ?? []}
                      onChange={s.handleModel}
                      disabled={!s.version}
                    />
                  </div>

                  {/* Scheduler */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "4px 10px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 9, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--theme-text-secondary)", opacity: 0.6 }}>
                      <LucideIcon name="circle-dot" size={9} />
                      <span>Scheduler</span>
                    </div>
                    <ArtDropdownPicker
                      value={s.scheduler}
                      placeholder="Choose scheduler…"
                      options={s.availableSchedulers}
                      onChange={s.handleScheduler}
                      disabled={!s.version || s.availableSchedulers.length === 0}
                    />
                  </div>
                </div>,
                document.body
              )}

              {/* Embeddings (disabled when Z-Image Turbo is selected) */}
              <ToolbarIconBtn
                title={s.isMultiPrompt
                  ? `Embeddings${s.activeEmbeddings.length > 0 ? ` (${s.activeEmbeddings.length})` : ""}`
                  : "Embeddings unavailable for Z-Image"
                }
                onClick={() => s.togglePanel("embeddings")}
                active={s.openPanel === "embeddings"}
                badge={s.activeEmbeddings.length > 0 ? s.activeEmbeddings.length : undefined}
                disabled={!s.isMultiPrompt}
              >
                <LucideIcon name="scan-text" size={14} />
              </ToolbarIconBtn>

              {/* LoRA */}
              <ToolbarIconBtn
                title={`LoRA${s.activeLoras.length > 0 ? ` (${s.activeLoras.length})` : ""}`}
                onClick={() => s.togglePanel("lora")}
                active={s.openPanel === "lora"}
                badge={s.activeLoras.length > 0 ? s.activeLoras.length : undefined}
              >
                <LucideIcon name="puzzle" size={14} />
              </ToolbarIconBtn>

              <div ref={s.settingsBtnRef}>
                <ToolbarIconBtn
                  title="Generation settings"
                  onClick={() => s.togglePopup("settings")}
                  active={s.openPopup === "settings"}
                >
                  <LucideIcon name="settings-2" size={14} />
                </ToolbarIconBtn>
              </div>

              {/* Seed toggle */}
              <ToolbarIconBtn
                title={s.seedRandomized ? "Seed: switch to fixed" : "Seed: switch to random"}
                onClick={s.handleToggleRandom}
                active={s.seedRandomized}
              >
                <LucideIcon name="shuffle" size={14} />
              </ToolbarIconBtn>

              {s.openPopup === "settings" && s.settingsAnchor && createPortal(
                <div id="art-settings-popup" className="bg-theme-panel overflow-y-auto" style={{
                  position: "fixed",
                  left: s.settingsAnchor.left,
                  bottom: s.settingsAnchor.bottom,
                  border: "1px solid rgba(255,255,255,0.14)",
                  borderRadius: 6,
                  zIndex: 1300,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                  maxHeight: 400,
                  minWidth: 260,
                }}>
                  <SettingsPopup
                    steps={s.steps}
                    cfgScale={s.cfgScale}
                    nSamples={s.nSamples}
                    imagesPerBatch={s.imagesPerBatch}
                    onStepsChange={(v) => { s.setSteps(v); saveToStorage("steps", v); s.persistGen({ steps: v }); }}
                    onCfgScaleChange={(v) => { s.setCfgScale(v); saveToStorage("cfg_scale", v); s.persistGen({ cfg_scale: v }); }}
                    onNSamplesChange={(v) => { s.setNSamples(v); saveToStorage("n_samples", v); s.persistGen({ n_samples: v }); }}
                    onImagesPerBatchChange={(v) => { s.setImagesPerBatch(v); saveToStorage("images_per_batch", v); s.persistGen({ images_per_batch: v }); }}
                  />
                </div>,
                document.body
              )}

              {s.openPopup === "promptSettings" && s.promptSettingsAnchor && createPortal(
                <div
                  id="art-prompt-settings-popup"
                  className="bg-theme-panel"
                  style={{
                    position: "fixed",
                    left: s.promptSettingsAnchor.left,
                    bottom: s.promptSettingsAnchor.bottom,
                    border: "1px solid rgba(255,255,255,0.14)",
                    borderRadius: 6,
                    zIndex: 1300,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                    minWidth: 180,
                    overflow: "hidden",
                  }}
                  onMouseDown={(e) => e.stopPropagation()}
                >
                  {/* New Prompt */}
                  <button
                    type="button"
                    onClick={() => { s.handleClearPrompts(); s.togglePopup("promptSettings"); }}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      width: "100%", padding: "8px 12px",
                      border: "none", background: "transparent",
                      color: "var(--theme-text)", cursor: "pointer",
                      fontSize: "0.8rem",
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                  >
                    <LucideIcon name="message-square-plus" size={14} />
                    <span>New Prompt</span>
                  </button>

                  {/* Save Prompt */}
                  <button
                    type="button"
                    onClick={() => { s.handleSavePrompt(); s.togglePopup("promptSettings"); }}
                    disabled={s.saving || !s.prompt.trim()}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      width: "100%", padding: "8px 12px",
                      border: "none", background: "transparent",
                      color: "var(--theme-text)", cursor: s.saving || !s.prompt.trim() ? "default" : "pointer",
                      fontSize: "0.8rem", opacity: s.saving || !s.prompt.trim() ? 0.4 : 1,
                    }}
                    onMouseEnter={(e) => {
                      if (!(s.saving || !s.prompt.trim()))
                        (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)";
                    }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                  >
                    <LucideIcon name={s.saving ? "loader" : "save"} size={14} />
                    <span>Save Prompt</span>
                  </button>

                  {/* Load saved prompts */}
                  <button
                    type="button"
                    onClick={() => { s.togglePanel("savedPrompts"); s.togglePopup("promptSettings"); }}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      width: "100%", padding: "8px 12px",
                      border: "none", background: "transparent",
                      color: "var(--theme-text)", cursor: "pointer",
                      fontSize: "0.8rem",
                      borderTop: "1px solid rgba(255,255,255,0.08)",
                    }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.06)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; }}
                  >
                    <LucideIcon name="folder-open" size={14} />
                    <span>Load saved prompts</span>
                  </button>
                </div>,
                document.body
              )}

              <span className="flex-grow-1" />

              {/* Generation type */}
              <div ref={genTypeBtnRef}>
                <button
                  type="button"
                  title="Generation type"
                  onClick={handleToggleGenType}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    height: 26, padding: "0 6px",
                    background: showGenType ? "rgba(255,255,255,0.08)" : "transparent",
                    border: "none", cursor: "pointer", borderRadius: 4,
                    color: showGenType ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
                    flexShrink: 0,
                    fontSize: 11, fontWeight: 700, letterSpacing: "0.03em",
                    fontVariant: "small-caps",
                    whiteSpace: "nowrap",
                  }}
                  onMouseEnter={(e) => {
                    if (!showGenType) {
                      e.currentTarget.style.color = "rgba(255,255,255,0.85)";
                      e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!showGenType) {
                      e.currentTarget.style.color = "rgba(255,255,255,0.45)";
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                >
                  <LucideIcon name="image-plus" size={13} />
                </button>
              </div>
              {showGenType && genTypeAnchor && createPortal(
                <div
                  id="art-gen-type-popup"
                  className="bg-theme-panel d-flex flex-column"
                  style={{
                    position: "fixed",
                    left: genTypeAnchor.left,
                    bottom: genTypeAnchor.bottom,
                    border: "1px solid rgba(255,255,255,0.14)",
                    borderRadius: 6,
                    zIndex: 1300,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                    minWidth: 180,
                    padding: "8px 0",
                    gap: 2,
                  }}
                >
                  <div style={{
                    fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
                    textTransform: "uppercase", color: "var(--theme-text-secondary)",
                    opacity: 0.6, padding: "4px 10px 6px",
                  }}>Generation Type</div>

                  <button
                    type="button"
                    onClick={() => { s.setGenerationType("txt2img"); setShowGenType(false); }}
                    style={{
                      display: "flex", flexDirection: "column", gap: 1,
                      width: "100%", padding: "6px 12px",
                      border: "none", background: s.generationType === "txt2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent",
                      cursor: "pointer", textAlign: "left",
                      color: s.generationType === "txt2img" ? "var(--bs-primary)" : "var(--theme-text)",
                      fontSize: "0.78rem",
                      borderLeft: s.generationType === "txt2img" ? "2px solid var(--bs-primary)" : "2px solid transparent",
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(var(--theme-text-rgb), 0.08)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = s.generationType === "txt2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent"; }}
                  >
                    <span>Text-to-image</span>
                    <span style={{ fontSize: "0.65rem", opacity: 0.55, fontWeight: 400 }}>
                      Generate from a text description alone
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => { s.setGenerationType("img2img"); setShowGenType(false); }}
                    style={{
                      display: "flex", flexDirection: "column", gap: 1,
                      width: "100%", padding: "6px 12px",
                      border: "none", background: s.generationType === "img2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent",
                      cursor: "pointer", textAlign: "left",
                      color: s.generationType === "img2img" ? "var(--bs-primary)" : "var(--theme-text)",
                      fontSize: "0.78rem",
                      borderLeft: s.generationType === "img2img" ? "2px solid var(--bs-primary)" : "2px solid transparent",
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(var(--theme-text-rgb), 0.08)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = s.generationType === "img2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent"; }}
                  >
                    <span>Image-to-image</span>
                    <span style={{ fontSize: "0.65rem", opacity: 0.55, fontWeight: 400 }}>
                      Transform an existing image with a text prompt
                    </span>
                  </button>
                </div>,
                document.body
              )}

              {/* Size picker */}
              <div ref={sizeBtnRef}>
                <button
                  type="button"
                  title="Image size"
                  onClick={handleSizeToggle}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    height: 26, padding: "0 6px",
                    background: showSize ? "rgba(255,255,255,0.08)" : "transparent",
                    border: "none", cursor: "pointer", borderRadius: 4,
                    color: showSize ? "var(--bs-primary)" : "rgba(255,255,255,0.45)",
                    flexShrink: 0,
                    fontSize: 10, fontWeight: 700, letterSpacing: "0.03em",
                  }}
                  onMouseEnter={(e) => {
                    if (!showSize) {
                      e.currentTarget.style.color = "rgba(255,255,255,0.85)";
                      e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!showSize) {
                      e.currentTarget.style.color = "rgba(255,255,255,0.45)";
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                >
                  <LucideIcon name="ruler-dimension-line" size={13} />
                </button>
              </div>
              {showSize && sizeAnchor && createPortal(
                <div id={sizePortalId} className="d-flex flex-column bg-theme-panel" style={{
                  position: "fixed", left: sizeAnchor.left, bottom: sizeAnchor.bottom,
                  border: "1px solid rgba(255,255,255,0.14)",
                  borderRadius: 6,
                  boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
                  padding: "10px 12px",
                  gap: 8,
                  zIndex: 1300,
                }}>
                  <div style={{
                    fontSize: 9, fontWeight: 700, letterSpacing: "0.07em",
                    textTransform: "uppercase", color: "var(--theme-text-secondary)",
                    opacity: 0.6, marginBottom: 6,
                  }}>Image Size</div>
                  <div className="d-flex align-items-center" style={{ gap: 6 }}>
                    <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>W</span>
                    <input
                      type="number" className="art-no-spin"
                      value={s.genWidth}
                      onChange={(e) => s.setGenWidth(Number(e.target.value))}
                      onBlur={(e) => { const v = Math.max(64, Math.min(2048, Number(e.target.value))); s.setGenWidth(v); saveToStorage("gen_width", v); s.persistGen({ width: v }); }}
                      style={{ height: 22, background: "var(--theme-input-bg)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "var(--theme-text)", fontSize: 10, textAlign: "center", padding: "0 2px", width: 56 }}
                    />
                  </div>
                  <div className="d-flex align-items-center" style={{ gap: 6 }}>
                    <span style={{ fontSize: 9, color: "var(--theme-text-secondary)", width: 10, flexShrink: 0 }}>H</span>
                    <input
                      type="number" className="art-no-spin"
                      value={s.genHeight}
                      onChange={(e) => s.setGenHeight(Number(e.target.value))}
                      onBlur={(e) => { const v = Math.max(64, Math.min(2048, Number(e.target.value))); s.setGenHeight(v); saveToStorage("gen_height", v); s.persistGen({ height: v }); }}
                      style={{ height: 22, background: "var(--theme-input-bg)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 4, color: "var(--theme-text)", fontSize: 10, textAlign: "center", padding: "0 2px", width: 56 }}
                    />
                  </div>
                </div>,
                document.body
              )}

            </div> : null}
            <div ref={s.toolbarRef} className="flex-shrink-0 d-flex flex-column">
              <PromptControls ref={s.controlsRef}
                generating={s.generating}
                progress={s.progress}
                phase={s.phase}
                hasPrompt={!!s.prompt.trim()}
                saving={s.saving}
                promptPopupOpen={s.openPopup === "promptSettings"}
                promptBtnRef={s.promptBtnRef}
                activeLoras={s.activeLoras}
                activeEmbeddings={s.activeEmbeddings}
                isMultiPrompt={s.isMultiPrompt}
                loraPanelOpen={s.openPanel === "lora"}
                embeddingsPanelOpen={s.openPanel === "embeddings"}
                seedRandomized={s.seedRandomized}
                onClear={s.handleClearPrompts}
                onSave={s.handleSavePrompt}
                onToggleSavedPrompts={() => s.togglePanel("savedPrompts")}
                onTogglePromptPopup={() => s.togglePopup("promptSettings")}
                onToggleLora={() => s.togglePanel("lora")}
                onToggleEmbeddings={() => s.togglePanel("embeddings")}
                onToggleRandom={s.handleToggleRandom}
                onGenerate={s.onGenerate}
                onCancel={s.onCancel}
              />
              </div>
          </div>
        </div>
      </div>

      {dropdownField && dropdownAnchor && createPortal(
        <div
          id="art-info-dropdown-popup"
          className="bg-theme-panel overflow-y-auto"
          style={{
            position: "fixed",
            left: dropdownAnchor.left,
            bottom: dropdownAnchor.bottom,
            minWidth: Math.max(dropdownAnchor.minWidth, 160),
            maxWidth: 280,
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 6,
            zIndex: 1300,
            boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
            maxHeight: 240,
          }}
        >
          {dropdownField === "gentype" ? (
            <>
              <button type="button"
                onClick={() => { s.setGenerationType("txt2img"); setDropdownField(null); }}
                style={{
                  display: "flex", flexDirection: "column", gap: 1,
                  width: "100%", padding: "6px 12px",
                  border: "none", background: s.generationType === "txt2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent",
                  cursor: "pointer", textAlign: "left",
                  color: s.generationType === "txt2img" ? "var(--bs-primary)" : "var(--theme-text)",
                  fontSize: "0.78rem",
                  borderLeft: s.generationType === "txt2img" ? "2px solid var(--bs-primary)" : "2px solid transparent",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(var(--theme-text-rgb), 0.08)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = s.generationType === "txt2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent"; }}
              >
                <span>Text-to-image</span>
                <span style={{ fontSize: "0.65rem", opacity: 0.55, fontWeight: 400 }}>Generate from a text description alone</span>
              </button>
              <button type="button"
                onClick={() => { s.setGenerationType("img2img"); setDropdownField(null); }}
                style={{
                  display: "flex", flexDirection: "column", gap: 1,
                  width: "100%", padding: "6px 12px",
                  border: "none", background: s.generationType === "img2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent",
                  cursor: "pointer", textAlign: "left",
                  color: s.generationType === "img2img" ? "var(--bs-primary)" : "var(--theme-text)",
                  fontSize: "0.78rem",
                  borderLeft: s.generationType === "img2img" ? "2px solid var(--bs-primary)" : "2px solid transparent",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(var(--theme-text-rgb), 0.08)"; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = s.generationType === "img2img" ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent"; }}
              >
                <span>Image-to-image</span>
                <span style={{ fontSize: "0.65rem", opacity: 0.55, fontWeight: 400 }}>Transform an existing image with a text prompt</span>
              </button>
            </>
          ) : (dropdownField === "version"
            ? (s.artOptions?.versions?.map((v) => ({ label: v.name, value: v.name })) ?? [])
            : dropdownField === "model"
              ? (s.artOptions?.versions?.find((v) => v.name === s.version)?.models ?? [])
              : s.availableSchedulers
          ).length === 0 ? (
            <div style={{ padding: "8px 12px", fontSize: "0.75rem", color: "var(--theme-text-secondary)" }}>
              No options
            </div>
          ) : (
            (dropdownField === "version"
              ? (s.artOptions?.versions?.map((v) => ({ label: v.name, value: v.name })) ?? [])
              : dropdownField === "model"
                ? (s.artOptions?.versions?.find((v) => v.name === s.version)?.models ?? [])
                : s.availableSchedulers
            ).map((opt: { label: string; value: string }) => {
              const currentValue = dropdownField === "version" ? s.version : dropdownField === "model" ? s.modelPath : s.scheduler;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    if (dropdownField === "version") s.handleVersion(opt.value);
                    else if (dropdownField === "model") s.handleModel(opt.value);
                    else s.handleScheduler(opt.value);
                    setDropdownField(null);
                  }}
                  style={{
                    display: "flex", alignItems: "center",
                    width: "100%", padding: "5px 12px",
                    background: opt.value === currentValue ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent",
                    border: "none",
                    borderLeft: opt.value === currentValue ? "2px solid var(--bs-primary)" : "2px solid transparent",
                    cursor: "pointer", textAlign: "left",
                    color: opt.value === currentValue ? "var(--bs-primary)" : "var(--theme-text)",
                    fontSize: "0.78rem",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.background =
                      opt.value === currentValue ? "rgba(var(--theme-primary-rgb), 0.18)" : "rgba(var(--theme-text-rgb), 0.08)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.background =
                      opt.value === currentValue ? "rgba(var(--theme-primary-rgb), 0.10)" : "transparent";
                  }}
                >
                  {opt.label}
                </button>
              );
            })
          )}
        </div>,
        document.body
      )}

      {s.openPanel && s.artPanelAnchor && (
        <div
          id="art-panel-popup"
          className="bg-theme-panel d-flex flex-column overflow-hidden"
          style={{
            position: "fixed",
            left: s.artPanelAnchor.left,
            bottom: s.artPanelAnchor.bottom,
            width: s.artPanelAnchor.width,
            height: s.artPanelAnchor.height,
            zIndex: 1300,
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 0,
            boxShadow: "4px -4px 24px rgba(0,0,0,0.7)",
          }}
        >
          {s.openPanel === "lora" && <LoraPanel />}
          {s.openPanel === "embeddings" && <EmbeddingsPanel />}
          {s.openPanel === "savedPrompts" && (
            <SavedPromptsPanel
              onLoad={s.handleLoadPrompt}
              onClose={() => s.togglePanel("savedPrompts")}
            />
          )}
        </div>
      )}
    </Fragment>
  );
}
