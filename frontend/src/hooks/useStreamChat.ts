import { useCallback, useRef, useState } from "react";
import { streamChatSSE } from "@/services/api";
import type { FileAttachment } from "@/types";

interface StreamCallbacks {
  onEvent: (eventType: string, data: string) => void;
  onDone: () => void;
  onError: (err: string) => void;
}

export function useStreamChat() {
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(
    (sessionId: string, message: string, callbacks: StreamCallbacks, attachments?: FileAttachment[]) => {
      setStreaming(true);
      setStreamingContent("");

      let accumulated = "";

      abortRef.current = streamChatSSE(
        sessionId,
        message,
        (eventType, data) => {
          if (eventType === "token") {
            accumulated += data;
            setStreamingContent(accumulated);
          } else {
            callbacks.onEvent(eventType, data);
          }
        },
        () => {
          setStreamingContent("");
          setStreaming(false);
          callbacks.onDone();
        },
        (err) => {
          setStreaming(false);
          setStreamingContent("");
          callbacks.onError(err);
        },
        attachments
      );
    },
    []
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, []);

  return { streaming, streamingContent, startStream, stopStream };
}
