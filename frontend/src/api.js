// This is the API contract to agree on:
//   GET    /sessions                  -> [{ id, title, updated_at }]
//   POST   /sessions                  -> { id, title, updated_at }
//   GET    /sessions/{id}/messages    -> [{ role: "user"|"bot", text }]
//   POST   /chat   { session_id, message } -> { session_id, response }
//   DELETE /sessions/{id}             -> { deleted: true }
//   PATCH  /sessions/{id} { title }   -> { id, title }
// ---------------------------------------------------------------------------

const USE_MOCK = true;
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Tiny in-memory "database" so the mock demo feels alive while you build.
let mockSessions = [
  { id: "s1", title: "Best pizza toppings", updated_at: Date.now() - 1000 * 60 * 60 },
  { id: "s2", title: "Explain attention mechanism", updated_at: Date.now() - 1000 * 60 * 30 },
];

let mockMessages = {
  s1: [
    { role: "user", text: "What's the best pizza topping?" },
    { role: "bot", text: "Margherita is the classic answer, but mushroom and truffle is criminally underrated." },
  ],
  s2: [
    { role: "user", text: "Explain the attention mechanism simply" },
    { role: "bot", text: "Attention lets the model decide which earlier words matter most when producing the current word - like highlighting the relevant part of a sentence before answering." },
  ],
};

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getSessions() {
  if (USE_MOCK) {
    await delay(300);
    return [...mockSessions].sort((a, b) => b.updated_at - a.updated_at);
  }
  const res = await fetch(`${API_URL}/sessions`);
  if (!res.ok) throw new Error("Failed to load sessions");
  return res.json();
}

export async function createSession() {
  if (USE_MOCK) {
    await delay(150);
    const id = `s${Date.now()}`;
    const session = { id, title: "New chat", updated_at: Date.now() };
    mockSessions.push(session);
    mockMessages[id] = [];
    return session;
  }
  const res = await fetch(`${API_URL}/sessions`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

export async function getMessages(sessionId) {
  if (USE_MOCK) {
    await delay(200);
    return mockMessages[sessionId] || [];
  }
  const res = await fetch(`${API_URL}/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();
}

export async function sendMessage(sessionId, text) {
  if (USE_MOCK) {
    await delay(700 + Math.random() * 600);
    const reply = `(mock AI model reply) You said: "${text}". Once the real backend is connected, this will be an actual generated response.`;
    mockMessages[sessionId] = [
      ...(mockMessages[sessionId] || []),
      { role: "user", text },
      { role: "bot", text: reply },
    ];
    const session = mockSessions.find((s) => s.id === sessionId);
    if (session) {
      session.updated_at = Date.now();
      if (session.title === "New chat") session.title = text.slice(0, 30);
    }
    return { session_id: sessionId, response: reply };
  }
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message: text }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function deleteSession(sessionId) {
  if (USE_MOCK) {
    await delay(150);
    mockSessions = mockSessions.filter((s) => s.id !== sessionId);
    delete mockMessages[sessionId];
    return { deleted: true };
  }
  const res = await fetch(`${API_URL}/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
}

export async function renameSession(sessionId, title) {
  if (USE_MOCK) {
    await delay(150);
    const session = mockSessions.find((s) => s.id === sessionId);
    if (session) session.title = title;
    return { id: sessionId, title };
  }
  const res = await fetch(`${API_URL}/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to rename session");
  return res.json();
}
