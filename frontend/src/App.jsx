import { useEffect, useState, useRef } from "react";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import Login from "./components/Login";
import Register from "./components/Register";
import { useAuth } from "./hooks/useAuth";
import { sessionService } from "./services/sessionService";
import { messageService } from "./services/messageService";
import { fileService } from "./services/fileService";
import "./App.css";

export default function App() {
  const { accessToken, isLoading, setAccessToken } = useAuth();
  const [page, setPage] = useState("login");

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  // Tracks whether a backend tool (e.g. report generation) is running.
  // null = inactive, { status: "running"|"done", tool, filename?, fileId? }
  const [toolState, setToolState] = useState(null);

  const isStreamingRef = useRef(false);
  const assistantMsgIdRef = useRef(null);

  // Route Guard
  useEffect(() => {
    if (isLoading) return; // Wait for initial token refresh

    if (!accessToken && page === "chat") {
      setPage("login");
    } else if (accessToken && (page === "login" || page === "register")) {
      setPage("chat");
    }
  }, [accessToken, isLoading, page]);

  // Logout callback passed to services to handle 401s
  const handleUnauthorized = () => {
    setAccessToken(null); // This will trigger the route guard to go to 'login'
  };

  // Load sessions when entering chat page
  useEffect(() => {
    if (page === "chat" && accessToken) {
      sessionService.listSessions(accessToken, handleUnauthorized)
        .then((data) => {
          setSessions(data.sessions); // backend returns { sessions: [...], total: ... }
          if (data.sessions.length > 0) {
            setCurrentSessionId(data.sessions[0].id);
          }
        })
        .catch(console.error);
    }
  }, [page, accessToken]);

  // Load messages when selected chat changes
  useEffect(() => {
    if (!currentSessionId || page !== "chat" || !accessToken) return;
    if (isStreamingRef.current) return;
    
    sessionService.getSession(accessToken, currentSessionId, handleUnauthorized)
      .then((sessionData) => {
        // Backend returns a full session object with a messages array
        setMessages(sessionData.messages.map(m => ({
          id: m.id,
          role: m.role,
          text: m.content,
          feedback: m.feedback ? m.feedback.vote : null
        })));
      })
      .catch(console.error);
  }, [currentSessionId, page, accessToken]);

  const handleNavigate = (newPage) => {
    setPage(newPage);
  };

  async function handleNewChat() {
    try {
      const session = await sessionService.createSession(accessToken, handleUnauthorized);
      // The backend returns an empty session
      setSessions((prev) => [session, ...prev]);
      setCurrentSessionId(session.id);
      setMessages([]);
      setIsSidebarOpen(false);
    } catch (err) {
      console.error("Failed to create chat", err);
    }
  }

  function handleSelectSession(id) {
    setCurrentSessionId(id);
    setIsSidebarOpen(false);
  }

  async function handleDeleteSession(id) {
    try {
      await sessionService.deleteSession(accessToken, id, handleUnauthorized);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);

      if (id === currentSessionId) {
        setCurrentSessionId(remaining[0]?.id || null);
        if (remaining.length === 0) setMessages([]);
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  }

  async function handleRenameSession(id, title) {
    try {
      await sessionService.renameSession(accessToken, id, title, handleUnauthorized);
      setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)));
    } catch (err) {
      console.error("Failed to rename session", err);
    }
  }

  function generateLocalTitle(text) {
    const words = text.trim().split(/\s+/);
    if (words.length <= 5) return text.trim();
    return words.slice(0, 5).join(" ") + "...";
  }

  async function handleSend(text) {
    if (!text.trim()) return;

    const generatedTitle = generateLocalTitle(text);
    isStreamingRef.current = true;
    
    // Add user message to UI immediately
    setMessages((prev) => [...prev, { role: "user", text }]);
    setIsSending(true);

    let sessionId = currentSessionId;
    
    // Auto-create session on first message (Zero-State)
    if (!sessionId) {
      try {
        const session = await sessionService.createSession(accessToken, handleUnauthorized);
        session.title = generatedTitle;
        setSessions((prev) => [session, ...prev]);
        setCurrentSessionId(session.id);
        sessionId = session.id;
      } catch (err) {
        console.error("Failed to auto-create chat", err);
        setIsSending(false);
        isStreamingRef.current = false;
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: "Couldn't create a session. Please try again." },
        ]);
        return;
      }
    } else {
      setSessions(prev => prev.map(s => 
        (s.id === sessionId && !s.title) ? { ...s, title: generatedTitle } : s
      ));
    }

    try {
      await messageService.streamMessage(
        accessToken,
        sessionId,
        text,
        handleUnauthorized,
        // onToken: Append token to the assistant message
        (tokenStr) => {
          setMessages((prev) => {
            const next = [...prev];
            const msgId = assistantMsgIdRef.current;
            const msgIndex = next.findIndex(m => m.id === msgId);
            if (msgIndex === -1) {
              // Should not happen if onStart fires first
              next.push({ role: "assistant", text: tokenStr, id: msgId });
            } else {
              next[msgIndex] = {
                ...next[msgIndex],
                text: next[msgIndex].text + tokenStr
              };
            }
            return next;
          });
        },
        // onStart: Create the empty assistant message bubble
        (data) => {
          assistantMsgIdRef.current = data.assistant_message_id;
          setMessages((prev) => {
            const next = [...prev];
            next.push({ role: "assistant", text: "", id: data.assistant_message_id, feedback: null });
            return next;
          });
          setIsSending(false); // Hide generic typing indicator since streaming started
        },
        // onEnd: Clear toolState, stamp fileId onto message, refresh session list
        (data) => {
          isStreamingRef.current = false;

          // If this turn ended a tool call, attach the fileId to the confirmation bubble
          // so the download button persists after streaming ends.
          setToolState(prev => {
            if (prev?.status === "done" && prev?.fileId) {
              const fid = prev.fileId;
              setMessages(msgs => msgs.map(m =>
                m.id === data.assistant_message_id
                  ? { ...m, fileId: fid }
                  : m
              ));
            }
            return null; // Clear the status bar
          });

          sessionService.listSessions(accessToken, handleUnauthorized)
            .then(res => setSessions(res.sessions))
            .catch(console.error);
        },
        // onToolCall: Update the tool status bar state
        (data) => {
          if (data.status === "running") {
            setToolState({ status: "running", tool: data.tool });
          } else if (data.status === "done") {
            setToolState({
              status: "done",
              tool: data.tool,
              filename: data.filename,
              fileId: data.file_id,
            });
          }
        },
      );
    } catch (err) {
      isStreamingRef.current = false;
      setIsSending(false);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Couldn't reach the server. Please try again." },
      ]);
    }
  }

  async function handleFeedback(messageId, vote, currentVote) {
    try {
      if (currentVote === null) {
        // First time voting
        const fb = await messageService.submitFeedback(accessToken, messageId, vote, handleUnauthorized);
        setMessages(prev => prev.map(m => m.id === messageId ? { ...m, feedback: fb.vote } : m));
      } else if (currentVote !== vote) {
        // Changing vote
        const fb = await messageService.updateFeedback(accessToken, messageId, vote, handleUnauthorized);
        setMessages(prev => prev.map(m => m.id === messageId ? { ...m, feedback: fb.vote } : m));
      }
    } catch (err) {
      console.error("Feedback failed:", err);
    }
  }

  async function handleDownload(fileId, filename) {
    try {
      await fileService.downloadFile(accessToken, fileId, filename, handleUnauthorized);
    } catch (err) {
      console.error("Download failed:", err);
    }
  }

  // Show a loading screen while checking initial auth
  if (isLoading) {
    return <div className="app-loading">Loading...</div>;
  }

  if (page === "login") {
    return <Login onNavigate={handleNavigate} />;
  }

  if (page === "register") {
    return <Register onNavigate={handleNavigate} />;
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
        toolState={toolState}
        onSend={handleSend}
        onFeedback={handleFeedback}
        onDownload={handleDownload}
        onToggleSidebar={() => setIsSidebarOpen((open) => !open)}
      />
    </div>
  );
}
