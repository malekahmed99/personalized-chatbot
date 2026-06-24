import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import MessageInput from "./MessageInput";
import TypingIndicator from "./TypingIndicator";

export default function ChatWindow({ sessionTitle, messages, isSending, onSend, onToggleSidebar }) {
  const bottomRef = useRef(null);

  // Auto-scroll to the latest message whenever the conversation changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  return (
    <main className="chat-window">
      <header className="chat-header">
        <button className="menu-btn" onClick={onToggleSidebar} aria-label="Toggle chat history">
          ☰
        </button>
        <h2>{sessionTitle}</h2>
        <span className="status">
          <span className="status-dot" /> AI model online
        </span>
      </header>

      <div className="message-list">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Ask the AI model anything to start the conversation.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} text={msg.text} />
        ))}
        {isSending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      <MessageInput disabled={isSending} onSend={onSend} />
    </main>
  );
}
