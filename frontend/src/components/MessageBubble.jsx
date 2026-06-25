export default function MessageBubble({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={"message-row" + (isUser ? " from-user" : " from-bot")}>
      <div className="avatar">{isUser ? "Y" : "φ"}</div>
      <div className="bubble">{text}</div>
    </div>
  );
}
