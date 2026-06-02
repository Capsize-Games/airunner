const icon = (name: string) => `/icons/lucide/dark/${name}.svg`;

type PanelId =
  | "knowledge"
  | "history"
  | "llm_settings"
  | "art_model"
  | "lora"
  | "embeddings"
  | "layers"
  | "grid"
  | "image_browser"
  | "stats"
  | "civitai_browser";

export function LeftIconBar({
  showChat,
  leftPanel,
  ttsOn,
  sttOn,
  onToggleChat,
  onLeftPanel,
  onToggleTts,
  onToggleStt,
}: {
  showChat: boolean;
  leftPanel: PanelId | null;
  ttsOn: boolean;
  sttOn: boolean;
  onToggleChat: () => void;
  onLeftPanel: (id: PanelId) => void;
  onToggleTts: () => void;
  onToggleStt: () => void;
}) {
  const active = (id: PanelId, panel: PanelId | null) =>
    panel === id ? "active" : "";

  return (
    <div className="icon-bar left">
      <button
        className={showChat ? "active" : ""}
        onClick={onToggleChat}
        title="Toggle Chat"
      >
        <img src={icon("message-square-text")} alt="" />
      </button>
      <hr />
      <button
        className={active("knowledge", leftPanel)}
        onClick={() => onLeftPanel("knowledge")}
        title="Knowledge Base"
      >
        <img src={icon("book")} alt="" />
      </button>
      <button
        className={active("history", leftPanel)}
        onClick={() => onLeftPanel("history")}
        title="History"
      >
        <img src={icon("history")} alt="" />
      </button>
      <button
        className={active("llm_settings", leftPanel)}
        onClick={() => onLeftPanel("llm_settings")}
        title="LLM Settings"
      >
        <img src={icon("settings-2")} alt="" />
      </button>
      <div className="flex-spacer" />
      <button
        className={ttsOn ? "active" : ""}
        onClick={onToggleTts}
        title="Text to Speech"
      >
        <img src={icon("speaker")} alt="TTS" />
      </button>
      <button
        className={sttOn ? "active" : ""}
        onClick={onToggleStt}
        title="Speech to Text"
      >
        <img src={icon("mic")} alt="STT" />
      </button>
    </div>
  );
}

export function RightIconBar({
  showCanvas,
  rightPanel,
  onToggleCanvas,
  onRightPanel,
  onOpenSettings,
}: {
  showCanvas: boolean;
  rightPanel: PanelId | null;
  onToggleCanvas: () => void;
  onRightPanel: (id: PanelId) => void;
  onOpenSettings: () => void;
}) {
  const active = (id: PanelId, panel: PanelId | null) =>
    panel === id ? "active" : "";

  return (
    <div className="icon-bar right">
      <button
        className={showCanvas ? "active" : ""}
        onClick={onToggleCanvas}
        title="Canvas"
      >
        <img src={icon("image")} alt="Canvas" />
      </button>
      <hr />
      <button
        className={active("civitai_browser", rightPanel)}
        onClick={() => onRightPanel("civitai_browser")}
        title="CivitAI Browser"
      >
        <img src={icon("cloud")} alt="CivitAI" />
      </button>
      <button
        className={active("art_model", rightPanel)}
        onClick={() => onRightPanel("art_model")}
        title="Art Model"
      >
        <img src={icon("sparkles")} alt="Model" />
      </button>
      <button
        className={active("lora", rightPanel)}
        onClick={() => onRightPanel("lora")}
        title="LoRA"
      >
        <img src={icon("puzzle")} alt="LoRA" />
      </button>
      <button
        className={active("embeddings", rightPanel)}
        onClick={() => onRightPanel("embeddings")}
        title="Embeddings"
      >
        <img src={icon("scan-text")} alt="Embeddings" />
      </button>
      <button
        className={active("layers", rightPanel)}
        onClick={() => onRightPanel("layers")}
        title="Layers"
      >
        <img src={icon("layers")} alt="Layers" />
      </button>
      <button
        className={active("grid", rightPanel)}
        onClick={() => onRightPanel("grid")}
        title="Grid"
      >
        <img src={icon("grid-2x2-check")} alt="Grid" />
      </button>
      <button
        className={active("image_browser", rightPanel)}
        onClick={() => onRightPanel("image_browser")}
        title="Image Browser"
      >
        <img src={icon("images")} alt="Browser" />
      </button>
      <button
        className={active("stats", rightPanel)}
        onClick={() => onRightPanel("stats")}
        title="Stats"
      >
        <img src={icon("activity")} alt="Stats" />
      </button>
      <div className="flex-spacer" />
      <button onClick={onOpenSettings} title="Settings">
        <img src={icon("settings")} alt="Settings" />
      </button>
    </div>
  );
}
