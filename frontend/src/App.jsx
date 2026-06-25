import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import { getSessions, getMessages, createSession, sendMessage, deleteSession, renameSession } from "./api";
import "./App.css";

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Load the list of past chats once, when the app first mounts.
  useEffect(() => {
    getSessions().then((data) => {
      setSessions(data);
      if (data.length > 0) setCurrentSessionId(data[0].id);
    });
  }, []);

  // Whenever the selected chat changes, load its messages.
  useEffect(() => {
    if (!currentSessionId) return;
    getMessages(currentSessionId).then(setMessages);
  }, [currentSessionId]);

  async function handleNewChat() {
    const session = await createSession();
    setSessions((prev) => [session, ...prev]);
    setCurrentSessionId(session.id);
    setMessages([]);
    setIsSidebarOpen(false);
  }

  function handleSelectSession(id) {
    setCurrentSessionId(id);
    setIsSidebarOpen(false);
  }

  async function handleDeleteSession(id) {
    await deleteSession(id);
    const remaining = sessions.filter((s) => s.id !== id);
    setSessions(remaining);

    // If we just deleted the chat we were looking at, hand off to another one.
    // Changing currentSessionId here is enough - the useEffect above that
    // watches currentSessionId will automatically load the new chat's
    // messages. No extra fetch call needed in this function.
    if (id === currentSessionId) {
      setCurrentSessionId(remaining[0]?.id || null);
      if (remaining.length === 0) setMessages([]);
    }
  }

  async function handleRenameSession(id, title) {
    await renameSession(id, title);
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)));
  }

  async function handleSend(text) {
    if (!currentSessionId || !text.trim()) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setIsSending(true);
    try {
      const data = await sendMessage(currentSessionId, text);
      setMessages((prev) => [...prev, { role: "bot", text: data.response }]);
      const refreshed = await getSessions();
      setSessions(refreshed);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "bot", text: "Couldn't reach the server. Please try again." },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  const currentSession = sessions.find((s) => s.id === currentSessionId);

  return (
    <div className="app">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelect={handleSelectSession}
        onNewChat={handleNewChat}
        onDelete={handleDeleteSession}
        onRename={handleRenameSession}
        isOpen={isSidebarOpen}
      />
      <ChatWindow
        sessionTitle={currentSession?.title || "New chat"}
        messages={messages}
        isSending={isSending}
        onSend={handleSend}
        onToggleSidebar={() => setIsSidebarOpen((open) => !open)}
      />
    </div>
  );
}
