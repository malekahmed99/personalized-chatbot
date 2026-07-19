import { useState, useRef, useEffect } from "react";

export default function MessageInput({ disabled, onSend }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  // Auto-expand height on every text change
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";                          // reset to measure true scrollHeight
    el.style.height = el.scrollHeight + "px";          // grow to content, capped by CSS max-height
  }, [text]);

  function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
    // Collapse back to one line after send
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  return (
    <form className="message-input" onSubmit={handleSubmit}>
      <textarea
        ref={textareaRef}
        rows={1}
        placeholder="Message AI model..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) handleSubmit(e);
        }}
      />
      <button type="submit" disabled={disabled || !text.trim()}>
        Send
      </button>
    </form>
  );
}
