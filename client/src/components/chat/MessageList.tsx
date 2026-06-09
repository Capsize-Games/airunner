import { useState, useCallback } from "react";
import type { Message } from "../../types/api";
import EmptyPlaceholder from "./messages/EmptyPlaceholder";
import MessageBubble from "./messages/MessageBubble";
import StreamingBubble from "./messages/StreamingBubble";

export default function MessageList({
  messages,
  streamBuffer,
  thinkingBuffer,
  onDeleteMessage,
  onSubmitEdit,
  onCopyMessage,
  onPlayMessage,
}: {
  messages: Message[];
  streamBuffer?: string;
  thinkingBuffer?: string;
  onDeleteMessage?: (index: number) => void;
  onSubmitEdit?: (index: number, newContent: string) => void;
  onCopyMessage?: (content: string) => void;
  onPlayMessage?: (content: string) => void;
}) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");

  const handleStartEdit = useCallback((index: number, content: string) => {
    setEditingIndex(index);
    setEditContent(content);
  }, []);

  const handleCancelEdit = useCallback(() => {
    setEditingIndex(null);
    setEditContent("");
  }, []);

  const handleConfirmEdit = useCallback(() => {
    if (editingIndex === null || !editContent.trim()) return;
    onSubmitEdit?.(editingIndex, editContent.trim());
    setEditingIndex(null);
    setEditContent("");
  }, [editingIndex, editContent, onSubmitEdit]);

  const handleEditKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleConfirmEdit();
      }
      if (e.key === "Escape") handleCancelEdit();
    },
    [handleConfirmEdit, handleCancelEdit],
  );

  const isStreaming = !!(
    thinkingBuffer?.trim() ||
    (streamBuffer && streamBuffer.length > 0)
  );

  if (messages.length === 0 && !isStreaming) {
    return <EmptyPlaceholder />;
  }

  return (
    <div className="d-flex flex-column gap-2">
      {messages.map((msg, i) => (
        <MessageBubble
          key={`msg-${i}`}
          message={msg}
          index={i}
          editingIndex={editingIndex}
          editContent={editContent}
          onStartEdit={handleStartEdit}
          onCancelEdit={handleCancelEdit}
          onConfirmEdit={handleConfirmEdit}
          onEditContentChange={setEditContent}
          onEditKeyDown={handleEditKeyDown}
          onDelete={onDeleteMessage}
          onCopy={onCopyMessage}
          onPlay={onPlayMessage}
        />
      ))}
      {isStreaming && (
        <StreamingBubble
          thinkingBuffer={thinkingBuffer}
          streamBuffer={streamBuffer}
        />
      )}
    </div>
  );
}
