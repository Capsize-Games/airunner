import type { RefObject, MutableRefObject } from "react";
import type { ChatPanel } from "../types";
import type { useLLMWebSocket } from "../../../features/llm/useLLMWebSocket";
import ActiveToolsDisplay from "./ActiveToolsDisplay";
import ChatDocsRow from "./ChatDocsRow";
import ChatToolbar from "./ChatToolbar";

interface ChatInputAreaProps {
  input: string;
  setInput: (v: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  handleTextareaResize: (e: React.MouseEvent) => void;
  textareaDrag: MutableRefObject<boolean>;
  textareaH: number;
  inputAreaRef: RefObject<HTMLDivElement>;
  llm: ReturnType<typeof useLLMWebSocket>;
  openPanel: ChatPanel;
  togglePanel: (panel: NonNullable<ChatPanel>) => void;
  docCount: number;
  ttsOn: boolean;
  sttOn: boolean;
  onToggleTts?: () => void;
  onToggleStt?: () => void;
  handleSend: () => Promise<void>;
  handleCancel: () => void;
  handleNewConversation: () => Promise<void>;
}

export default function ChatInputArea({
  input,
  setInput,
  handleKeyDown,
  handleTextareaResize,
  textareaDrag,
  textareaH,
  inputAreaRef,
  llm,
  openPanel,
  togglePanel,
  docCount,
  ttsOn,
  sttOn,
  onToggleTts,
  onToggleStt,
  handleSend,
  handleCancel,
  handleNewConversation,
}: ChatInputAreaProps) {
  return (
    <>
      <div
        onMouseDown={handleTextareaResize}
        style={{
          height: 4,
          cursor: "row-resize",
          flexShrink: 0,
          background: "transparent",
          transition: "background 0.15s",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.background =
            "rgba(99,153,255,0.3)";
        }}
        onMouseLeave={(e) => {
          if (!textareaDrag.current) {
            (e.currentTarget as HTMLDivElement).style.background = "transparent";
          }
        }}
      />

      <div
        ref={inputAreaRef}
        className="chat-input-area"
        style={{
          height: textareaH,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            border: "none",
            borderRadius: 0,
            background: "#1a1a2e",
            minHeight: 0,
          }}
        >
          <textarea
            style={{
              resize: "none",
              flex: 1,
              background: "transparent",
              color: "var(--theme-text)",
              border: "none",
              outline: "none",
              padding: "8px 10px",
              minHeight: 0,
              fontFamily: "inherit",
              fontSize: "inherit",
            }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={llm.streaming}
          />

          <ActiveToolsDisplay activeTools={llm.activeTools} />

          <ChatDocsRow
            openPanel={openPanel}
            togglePanel={togglePanel}
            docCount={docCount}
          />

          <ChatToolbar
            ttsOn={ttsOn}
            sttOn={sttOn}
            onToggleTts={onToggleTts}
            onToggleStt={onToggleStt}
            streaming={llm.streaming}
            input={input}
            handleSend={handleSend}
            handleCancel={handleCancel}
            handleNewConversation={handleNewConversation}
          />
        </div>
      </div>
    </>
  );
}
