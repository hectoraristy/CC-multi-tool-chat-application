import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { getMessages, streamChatSSE } from "@/services/api";
import type { ChatMessage, ToolCall } from "@/types";

interface PendingTool {
  tool: string;
  args?: Record<string, unknown>;
  status: "calling" | "done";
  preview?: string;
}

export function useChat(sessionId: string | null) {
  const queryClient = useQueryClient();
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [pendingTools, setPendingTools] = useState<PendingTool[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const { data: messages = [] } = useQuery<ChatMessage[]>({
    queryKey: ["messages", sessionId],
    queryFn: () => getMessages(sessionId!),
    enabled: !!sessionId,
  });

  const sendMessage = useCallback(
    (content: string) => {
      if (!sessionId || streaming) return;

      const userMsg: ChatMessage = {
        message_id: crypto.randomUUID(),
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      queryClient.setQueryData<ChatMessage[]>(
        ["messages", sessionId],
        (old = []) => [...old, userMsg]
      );

      setStreaming(true);
      setStreamingContent("");
      setPendingTools([]);

      let accumulated = "";

      abortRef.current = streamChatSSE(
        sessionId,
        content,
        (eventType, data) => {
          if (eventType === "token") {
            accumulated += data;
            setStreamingContent(accumulated);
          } else if (eventType === "tool_call") {
            try {
              const tc: ToolCall = JSON.parse(data);
              setPendingTools((prev) => [
                ...prev,
                { tool: tc.tool, args: tc.args, status: "calling" },
              ]);
            } catch {
              /* ignore parse errors */
            }
          } else if (eventType === "tool_result") {
            try {
              const tr = JSON.parse(data);
              setPendingTools((prev) =>
                prev.map((pt) =>
                  pt.tool === tr.tool && pt.status === "calling"
                    ? { ...pt, status: "done", preview: tr.result_preview }
                    : pt
                )
              );
            } catch {
              /* ignore parse errors */
            }
          }
        },
        () => {
          setStreamingContent("");
          setStreaming(false);
          setPendingTools([]);
          queryClient.invalidateQueries({
            queryKey: ["messages", sessionId],
          });
        },
        (err) => {
          console.error("Stream error:", err);
          setStreaming(false);
          setStreamingContent("");
        }
      );
    },
    [sessionId, streaming, queryClient]
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, []);

  return {
    messages,
    streaming,
    streamingContent,
    pendingTools,
    sendMessage,
    stopStreaming,
  };
}
