import { readSSEStream } from "@/lib/sse";
import type { ChatMessage, FileAttachment, Session } from "@/types";

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
  const body = await res.json();
  return body.items;
}

export async function getMessages(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error(`Failed to get messages: ${res.statusText}`);
  return res.json();
}

export async function getToolResultDownloadUrl(
  sessionId: string,
  resultId: string
): Promise<string> {
  const res = await fetch(
    `${BASE_URL}/sessions/${sessionId}/tool-results/${resultId}/download`
  );
  if (!res.ok) throw new Error(`Failed to get download URL: ${res.statusText}`);

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const body = await res.json();
    return body.download_url;
  }

  const text = await res.text();
  return URL.createObjectURL(new Blob([text], { type: "text/plain" }));
}

export async function uploadFile(
  sessionId: string,
  file: File
): Promise<FileAttachment> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", file);

  const res = await fetch(`${BASE_URL}/chat/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`Upload failed: ${detail}`);
  }
  return res.json();
}

export function streamChatSSE(
  sessionId: string,
  message: string,
  onEvent: (eventType: string, data: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
  attachments?: FileAttachment[]
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const payload: Record<string, unknown> = {
        session_id: sessionId,
        message,
      };
      if (attachments?.length) {
        payload.attachments = attachments;
      }

      const res = await fetch(`${BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
      if (!res.body) throw new Error("No response body");

      let terminated = false;

      await readSSEStream(res.body, ({ event, data }) => {
        if (terminated) return;

        if (event === "done") {
          terminated = true;
          onDone();
        } else if (event === "error") {
          terminated = true;
          onError(data);
        } else {
          onEvent(event, data);
        }
      });

      if (!terminated) onDone();
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      onError(err instanceof Error ? err.message : String(err));
    }
  })();

  return controller;
}
