import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Card from "react-bootstrap/Card";
import Form from "react-bootstrap/Form";
import Button from "react-bootstrap/Button";
import Spinner from "react-bootstrap/Spinner";
import { streamLLM, createConversation } from "../../api/client";
import type { Message } from "../../types/api";
import MessageList from "./MessageList";

export default function ChatView() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");

  const scrollToBottom = useCallback(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamBuffer, scrollToBottom]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");

    const userMsg: Message = { role: "user", content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setStreaming(true);
    setStreamBuffer("");

    try {
      const gen = streamLLM(newMessages);
      let fullResponse = "";
      for await (const chunk of gen) {
        if (chunk.done) break;
        if (chunk.error) {
          setMessages([
            ...newMessages,
            { role: "assistant", content: `Error: ${chunk.error}` },
          ]);
          break;
        }
        fullResponse += chunk.token ?? "";
        setStreamBuffer(fullResponse);
      }
      if (fullResponse) {
        setMessages([
          ...newMessages,
          { role: "assistant", content: fullResponse },
        ]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Stream failed";
      setMessages([
        ...newMessages,
        { role: "assistant", content: `Error: ${msg}` },
      ]);
    } finally {
      setStreamBuffer("");
      setStreaming(false);
    }
  }, [input, messages, streaming]);

  return (
    <Card className="d-flex flex-column" style={{ height: "calc(100vh - 120px)" }}>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span>💬 Chat</span>
        <Button
          variant="outline-secondary"
          size="sm"
          onClick={async () => {
            try {
              await createConversation();
              setMessages([]);
              navigate("/chat");
            } catch { /* */ }
          }}
        >
          New Chat
        </Button>
      </Card.Header>
      <Card.Body className="overflow-auto flex-grow-1">
        <MessageList messages={messages} streamBuffer={streamBuffer} />
      </Card.Body>
      <Card.Footer>
        <Form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <div className="d-flex gap-2">
            <Form.Control
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              disabled={streaming}
              autoFocus
            />
            <Button
              type="submit"
              variant="primary"
              disabled={streaming || !input.trim()}
            >
              {streaming ? <Spinner animation="border" size="sm" /> : "Send"}
            </Button>
          </div>
        </Form>
      </Card.Footer>
    </Card>
  );
}
