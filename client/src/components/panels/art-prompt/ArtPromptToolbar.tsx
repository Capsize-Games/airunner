import { useState, useEffect } from "react";
import {
  getArtModelOptions,
  updateSingleton,
} from "../../../api/client";
import type { ArtOptionsResponse } from "../../../api/client";

export default function ArtPromptToolbar() {
  const [options, setOptions] = useState<ArtOptionsResponse | null>(null);
  const [version, setVersion] = useState(() => {
    try { return localStorage.getItem("airunner_art_version") || ""; }
    catch { return ""; }
  });
  const [modelPath, setModelPath] = useState(() => {
    try { return localStorage.getItem("airunner_art_model") || ""; }
    catch { return ""; }
  });
  const [scheduler, setScheduler] = useState(() => {
    try { return localStorage.getItem("airunner_art_scheduler") || ""; }
    catch { return ""; }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getArtModelOptions()
      .then(setOptions)
      .catch(() => {/* server may be unavailable */})
      .finally(() => setLoading(false));
  }, []);

  const versionInfo = options?.versions?.find((v) => v.name === version);
  const availableModels = versionInfo?.models ?? [];
  const availableSchedulers = versionInfo?.schedulers ?? [];

  const handleVersion = (v: string) => {
    setVersion(v);
    setModelPath("");
    setScheduler("");
    try { localStorage.setItem("airunner_art_version", v); } catch {/* */ }
    updateSingleton("GeneratorSettings", {
      version: v,
      custom_path: "",
      scheduler: "",
    }).catch(() => {});
    window.dispatchEvent(
      new CustomEvent("art-version-changed", { detail: v }),
    );
  };

  const handleModel = (m: string) => {
    setModelPath(m);
    try { localStorage.setItem("airunner_art_model", m); } catch {/* */ }
    updateSingleton("GeneratorSettings", { custom_path: m }).catch(() => {});
    window.dispatchEvent(
      new CustomEvent("art-model-changed", { detail: m }),
    );
  };

  const handleScheduler = (s: string) => {
    setScheduler(s);
    try { localStorage.setItem("airunner_art_scheduler", s); } catch {/* */ }
    updateSingleton("GeneratorSettings", { scheduler: s }).catch(() => {});
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "4px 8px",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        background: "var(--theme-panel-bg)",
        flexShrink: 0,
      }}
    >
      {loading && (
        <div
          className="spinner-border spinner-border-sm"
          role="status"
          style={{
            color: "var(--theme-text-secondary)",
            width: 12,
            height: 12,
          }}
        />
      )}
      <select
        className="form-select form-select-sm"
        style={{ width: "auto", minWidth: 110, fontSize: 11 }}
        value={version}
        disabled={loading}
        onChange={(e) => handleVersion(e.target.value)}
      >
        <option value="">Version...</option>
        {(options?.versions ?? []).map((v) => (
          <option key={v.name} value={v.name}>{v.name}</option>
        ))}
      </select>
      <select
        className="form-select form-select-sm"
        style={{ width: "auto", minWidth: 130, fontSize: 11 }}
        value={modelPath}
        disabled={loading || !version || availableModels.length === 0}
        onChange={(e) => handleModel(e.target.value)}
      >
        <option value="">
          {!version ? "Version..." : "Model..."}
        </option>
        {availableModels.map((m) => (
          <option key={m.value} value={m.value}>{m.label}</option>
        ))}
      </select>
      <select
        className="form-select form-select-sm"
        style={{ width: "auto", minWidth: 130, fontSize: 11 }}
        value={scheduler}
        disabled={loading || !version}
        onChange={(e) => handleScheduler(e.target.value)}
      >
        <option value="">Scheduler...</option>
        {availableSchedulers.map((s) => (
          <option key={s.value} value={s.value}>{s.label}</option>
        ))}
      </select>
    </div>
  );
}
