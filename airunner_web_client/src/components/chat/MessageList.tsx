import type { Message } from "../../types/api";
import Alert from "react-bootstrap/Alert";

export default function MessageList({
  messages,
  streamBuffer,
}: {
  messages: Message[];
  streamBuffer?: string;
}) {
  if (messages.length === 0 && !streamBuffer) {
    return (
      <div className="text-muted text-center mt-5">
        <p>Start a conversation by typing a message below.</p>
      </div>
    );
  }

  return (
    <div className="d-flex flex-column gap-2">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {streamBuffer ? (
        <MessageBubble
          message={{ role: "assistant", content: streamBuffer }}
          streaming
        />
      ) : null}
    </div>
  );
}

function MessageBubble({
  message,
  streaming,
}: {
  message: Message;
  streaming?: boolean;
}) {
  const isUser = message.role === "user";
  return (
    <Alert
      variant={isUser ? "primary" : "secondary"}
      className={`mb-1 ${isUser ? "ms-auto" : "me-auto"}`}
      style={{ maxWidth: "80%", whiteSpace: "pre-wrap" }}
    >
      <small className="fw-bold">{isUser ? "You" : "AI"}</small>
      <div className={streaming ? "streaming-cursor" : ""}>
        {message.content}
      </div>
    </Alert>
  );
}
