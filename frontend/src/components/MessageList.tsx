import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/EmptyState";
import { MessageBubble } from "@/components/MessageBubble";
import { StreamingIndicator } from "@/components/StreamingIndicator";
import { ThinkingIndicator } from "@/components/ThinkingIndicator";
import { ToolCallInlineMessage } from "@/components/ToolCallInlineMessage";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import type { ChatMessage } from "@/types";

interface Props {
  messages: ChatMessage[];
  streamingContent: string;
  streaming: boolean;
}

export function MessageList({ messages, streamingContent, streaming }: Props) {
  const endRef = useAutoScroll([messages, streamingContent, streaming]);
  const isEmpty = messages.length === 0 && !streamingContent && !streaming;

  return (
    <ScrollArea className="flex-1 min-h-0">
      <div className="px-4 py-6 space-y-4">
        {isEmpty && <EmptyState />}

        {messages.map((msg) =>
          msg.role === "tool_call" ? (
            <div key={msg.message_id} className="flex justify-start">
              <ToolCallInlineMessage
                tool={msg.tool_name || "unknown"}
                args={msg.tool_args}
              />
            </div>
          ) : (
            <MessageBubble key={msg.message_id} message={msg} />
          )
        )}

        <StreamingIndicator content={streamingContent} />
        {streaming && !streamingContent && <ThinkingIndicator />}

        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
}
