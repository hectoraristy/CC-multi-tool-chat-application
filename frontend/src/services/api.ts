import type { ChatMessage, Session } from "@/types";

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export async function createSession(
  title: string = "New Chat"
): Promise<Session> {
  const res = await fetch(`${BASE_URL}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
  return res.json();
}

export async function updateSession(
  sessionId: string,
  title: string
): Promise<Session> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error(`Failed to update session: ${res.statusText}`);
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Failed to delete session: ${res.statusText}`);
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${BASE_URL}/sessions`);
  if (!res.ok) throw new Error(`Failed to list sessions: ${res.statusText}`);
  return res.json();
}

export async function getMessages(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`Failed to get messages: ${res.statusText}`);
  return res.json();
}

export function streamChatSSE(
  sessionId: string,
  message: string,
  onEvent: (eventType: string, data: string) => void,
  onDone: () => void,
  onError: (err: string) => void
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ session_id: sessionId, message }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        buffer = buffer.replace(/\r\n/g, "\n");
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          let eventType = "message";
          let data = "";

          for (const line of part.split("\n")) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              data = line.slice(5).trim();
            }
          }

          if (eventType === "done") {
            onDone();
            return;
          }

          if (eventType === "error") {
            onError(data);
            return;
          }

          onEvent(eventType, data);
        }
      }

      onDone();
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      onError(err instanceof Error ? err.message : String(err));
    }
  })();

  return controller;
}
