import {
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import Alert from "react-bootstrap/Alert";
import Button from "react-bootstrap/Button";
import Form from "react-bootstrap/Form";
import Spinner from "react-bootstrap/Spinner";
import {
  streamLLM,
  listLLMModels,
  getSingleton,
  updateSingleton,
} from "../../api/client";
import type { Message, ResourceRecord } from "../../types/api";
import MessageList from "./MessageList";

interface ModelOption {
  label: string;
  value: string;
  pipeline_action: string;
}

export default function ChatView() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    listLLMModels().then(setModels).catch(() => {});
    getSingleton("LLMGeneratorSettings")
      .then((r: ResourceRecord) =>
        setSelectedModel(String(r.model_path ?? "")),
      )
      .catch(() => {});
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;
    if (!selectedModel) {
      setError("Please select an LLM model in Settings first.");
      return;
    }
    setError(null);
    setInput("");

    const userMsg: Message = { role: "user", content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setStreaming(true);
    setStreamBuffer("");

    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);

    try {
      const gen = streamLLM(newMessages, controller.signal);
      let fullResponse = "";
      for await (const chunk of gen) {
        if (chunk.done) break;
        if (chunk.error) {
          setError(chunk.error);
          break;
        }
        fullResponse += chunk.token ?? "";
        setStreamBuffer(fullResponse);
      }
      if (fullResponse && !controller.signal.aborted) {
        setMessages([
          ...newMessages,
          { role: "assistant", content: fullResponse },
        ]);
      }
    } catch (err: unknown) {
      if (!controller.signal.aborted) {
        const msg = err instanceof Error ? err.message : "Stream failed";
        setError(msg);
      }
    } finally {
      setStreamBuffer("");
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, messages, streaming, selectedModel]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
    setStreamBuffer("");
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleModelChange = (path: string) => {
    setSelectedModel(path);
    updateSingleton("LLMGeneratorSettings", { model_path: path }).catch(
      () => {},
    );
  };

  return (
    <div className="d-flex flex-column h-100">
      {/* Error banner */}
      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Messages */}
      <div className="chat-messages p-2 flex-grow-1">
        <MessageList messages={messages} streamBuffer={streamBuffer} />
      </div>

      {/* Input area */}
      <div className="chat-input-area border-top p-2 bg-body-tertiary">
        <Form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <Form.Group className="mb-2">
            <Form.Select
              size="sm"
              value={selectedModel}
              onChange={(e) => handleModelChange(e.target.value)}
            >
              <option value="">Select LLM model...</option>
              {models
                .filter((m) => m.pipeline_action !== "embedding")
                .map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
            </Form.Select>
          </Form.Group>
          <Form.Group className="mb-2">
            <Form.Control
              as="textarea"
              rows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
              disabled={streaming}
            />
          </Form.Group>
          <div className="d-flex justify-content-end">
            {streaming ? (
              <Button variant="danger" size="sm" onClick={handleCancel}>
                <Spinner animation="border" size="sm" className="me-1" />
                Cancel
              </Button>
            ) : (
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={!input.trim() || !selectedModel}
              >
                Send
              </Button>
            )}
          </div>
        </Form>
      </div>
    </div>
  );
}
