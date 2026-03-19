import { ScrollArea } from "@/components/ui/scroll-area";
import { ToolResultCard } from "@/components/ToolResultCard";
import type { ChatMessage } from "@/types";
import { cn } from "@/lib/utils";
import { useEffect, useRef } from "react";

interface PendingTool {
  tool: string;
  args?: Record<string, unknown>;
  status: "calling" | "done";
  preview?: string;
}

interface Props {
  messages: ChatMessage[];
  streamingContent: string;
  pendingTools: PendingTool[];
}

export function MessageList({ messages, streamingContent, pendingTools }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, pendingTools]);

  return (
    <ScrollArea className="flex-1">
      <div className="px-4 py-6 space-y-4">
        {messages.length === 0 && !streamingContent && pendingTools.length === 0 && (
          <div className="flex items-center justify-center h-full min-h-[50vh]">
            <div className="text-center text-muted-foreground">
              <h2 className="text-xl font-semibold mb-2">Multi-Tool Chat</h2>
              <p className="text-sm">
                Ask me anything. I can query databases, fetch web pages, call
                APIs, and read files.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.message_id}
            className={cn(
              "flex",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[75%] rounded-2xl px-4 py-3",
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-card-foreground border border-border"
              )}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {pendingTools.length > 0 && (
          <div className="flex justify-start">
            <div className="max-w-[75%] space-y-1">
              {pendingTools.map((pt, i) => (
                <ToolResultCard
                  key={`${pt.tool}-${i}`}
                  tool={pt.tool}
                  args={pt.args}
                  status={pt.status}
                  preview={pt.preview}
                />
              ))}
            </div>
          </div>
        )}

        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-2xl px-4 py-3 bg-card text-card-foreground border border-border">
              <p className="text-sm whitespace-pre-wrap">{streamingContent}</p>
              <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-0.5" />
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
}
