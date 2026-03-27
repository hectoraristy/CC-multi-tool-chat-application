import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { getMessages, uploadFile } from "@/services/api";
import { useStreamChat } from "@/hooks/useStreamChat";
import { queryKeys } from "@/lib/queryKeys";
import type { ChatMessage, FileAttachment, ToolCall } from "@/types";

export function useChat(sessionId: string | null) {
  const queryClient = useQueryClient();
  const { streaming, streamingContent, startStream, stopStream } = useStreamChat();
  const [uploading, setUploading] = useState(false);

  const { data: messages = [] } = useQuery<ChatMessage[]>({
    queryKey: queryKeys.messages(sessionId!),
    queryFn: () => getMessages(sessionId!),
    enabled: !!sessionId,
  });

  const sendMessage = useCallback(
    async (content: string, file?: File) => {
      if (!sessionId || streaming || uploading) return;

      let attachments: FileAttachment[] | undefined;

      if (file) {
        try {
          setUploading(true);
          const attachment = await uploadFile(sessionId, file);
          attachments = [attachment];
        } catch (err) {
          console.error("File upload failed:", err);
          setUploading(false);
          return;
        } finally {
          setUploading(false);
        }
      }

      const userMsg: ChatMessage = {
        message_id: crypto.randomUUID(),
        role: "user",
        content,
        attachments,
        created_at: new Date().toISOString(),
      };

      const msgKey = queryKeys.messages(sessionId);

      queryClient.setQueryData<ChatMessage[]>(
        msgKey,
        (old = []) => [...old, userMsg]
      );

      startStream(sessionId, content, {
        onEvent: (eventType, data) => {
          if (eventType === "tool_call") {
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
                msgKey,
                (old = []) => [...old, toolCallMsg]
              );
            } catch {
              /* ignore parse errors */
            }
          }
        },
        onDone: () => {
          queryClient.invalidateQueries({ queryKey: msgKey });
        },
        onError: (err) => {
          console.error("Stream error:", err);
        },
      }, attachments);
    },
    [sessionId, streaming, uploading, queryClient, startStream]
  );

  return {
    messages,
    streaming,
    streamingContent,
    uploading,
    sendMessage,
    stopStreaming: stopStream,
  };
}
