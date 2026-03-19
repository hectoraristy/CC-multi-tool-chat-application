import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { getMessages, streamChatSSE } from "@/services/api";
import type { ChatMessage, ToolCall } from "@/types";

export function useChat(sessionId: string | null) {
  const queryClient = useQueryClient();
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
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
              const toolCallMsg: ChatMessage = {
                message_id: crypto.randomUUID(),
                role: "tool_call",
                content: JSON.stringify(tc.args),
                tool_name: tc.tool,
                tool_call_id: tc.id,
                tool_args: tc.args,
                created_at: new Date().toISOString(),
              };
              queryClient.setQueryData<ChatMessage[]>(
                ["messages", sessionId],
                (old = []) => [...old, toolCallMsg]
              );
            } catch {
              /* ignore parse errors */
            }
          }
        },
        () => {
          setStreamingContent("");
          setStreaming(false);
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
    sendMessage,
    stopStreaming,
  };
}
