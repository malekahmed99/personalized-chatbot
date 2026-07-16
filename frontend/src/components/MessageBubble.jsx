import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageBubble({ msg, onFeedback, onDownload }) {
  const isBot = msg.role === "assistant" || msg.role === "bot";

  // Pull the real filename out of the confirmation text if present,
  // e.g. "Incident report generated — Incident_Report_20260711_052200.md"
  const filenameMatch = msg.text?.match(/([\w\-]+\.md)/);
  const filename = filenameMatch ? filenameMatch[1] : "Incident_Report.md";

  return (
    <div className={`message-row ${!isBot ? "from-user" : "from-bot"}`}>
      <div className="avatar">{!isBot ? "U" : "AI"}</div>
      <div className="bubble-container">
        <div className="bubble">
          {isBot ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
          ) : (
            msg.text
          )}
        </div>
        {isBot && msg.id && (
          <div className="feedback-actions">
            <button 
              className={`feedback-btn ${msg.feedback === "up" ? "active" : ""}`}
              onClick={() => onFeedback(msg.id, "up", msg.feedback)}
              title="Helpful"
            >
              👍
            </button>
            <button 
              className={`feedback-btn ${msg.feedback === "down" ? "active" : ""}`}
              onClick={() => onFeedback(msg.id, "down", msg.feedback)}
              title="Not helpful"
            >
              👎
            </button>
          </div>
        )}
        {isBot && msg.fileId && (
          <button
            type="button"
            className="report-download-btn"
            onClick={() => onDownload?.(msg.fileId, filename)}
          >
            Download report
          </button>
        )}
      </div>
    </div>
  );
}
