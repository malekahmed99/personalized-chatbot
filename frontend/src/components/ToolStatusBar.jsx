export default function ToolStatusBar({ toolState }) {
  if (!toolState) return null;

  return (
    <div className="tool-status-bar">
      <span className="tool-status-dots">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
      <span className="tool-status-label">
        {toolState.status === "running"
          ? "Generating your report..."
          : `Report ready — ${toolState.filename}`}
      </span>
    </div>
  );
}
