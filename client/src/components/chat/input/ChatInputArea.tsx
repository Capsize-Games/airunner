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
        className="chat-input-area flex-shrink-0 d-flex flex-column"
        style={{ height: textareaH }}
      >
        <div className="flex-grow-1 d-flex flex-column min-h-0">
          <div
            className="d-flex flex-column min-h-0 prompt-textarea-bg"
            style={{ flex: 1, minHeight: 0 }}
          >
            <textarea
              className="flex-grow-1 min-h-0"
              style={{
                resize: "none",
                background: "transparent",
                color: "var(--theme-text)",
                border: "none",
                outline: "none",
                padding: "8px 10px",
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
          </div>

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
