import { apiFetch } from "./api";

export const messageService = {
  async streamMessage(token, sessionId, content, onUnauthorized,
                      onToken, onStart, onEnd, onToolCall) {
    const res = await apiFetch(`/api/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }, token, onUnauthorized);

    if (!res.ok) {
      throw new Error("Failed to send message");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // Split by double newline which separates SSE events
        const parts = buffer.split("\n\n");
        // The last part might be incomplete, so keep it in the buffer
        buffer = parts.pop() || "";

        for (const part of parts) {
          const lines = part.split("\n");
          let eventName = "message";
          let dataStr = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventName = line.substring(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.substring(6).trim();
            }
          }

          if (dataStr) {
            try {
              const data = JSON.parse(dataStr);
              if (eventName === "message_start" && onStart) {
                onStart(data);
              } else if (eventName === "token" && onToken) {
                onToken(data.token);
              } else if (eventName === "message_end" && onEnd) {
                onEnd(data);
              } else if (eventName === "tool_call" && onToolCall) {
                // data = { tool, status, filename?, file_id? }
                onToolCall(data);
              }
            } catch (e) {
              console.error("Failed to parse SSE JSON data", e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  async submitFeedback(token, messageId, vote, onUnauthorized) {
    const res = await apiFetch(`/api/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ vote }),
    }, token, onUnauthorized);
    
    if (!res.ok) {
      if (res.status === 409) {
        throw new Error("ALREADY_VOTED");
      }
      throw new Error("Failed to submit feedback");
    }
    return await res.json();
  },

  async updateFeedback(token, messageId, vote, onUnauthorized) {
    const res = await apiFetch(`/api/messages/${messageId}/feedback`, {
      method: "PATCH",
      body: JSON.stringify({ vote }),
    }, token, onUnauthorized);

    if (!res.ok) throw new Error("Failed to update feedback");
    return await res.json();
  }
};
