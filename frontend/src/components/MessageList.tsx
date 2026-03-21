import { ScrollArea } from "@/components/ui/scroll-area";
import { ToolCallInlineMessage } from "@/components/ToolCallInlineMessage";
import type { ChatMessage } from "@/types";
import { cn } from "@/lib/utils";
import { useEffect, useRef } from "react";

interface Props {
  messages: ChatMessage[];
  streamingContent: string;
  streaming: boolean;
}

export function MessageList({ messages, streamingContent, streaming }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, streaming]);

  return (
    <ScrollArea className="flex-1 min-h-0">
      <div className="px-4 py-6 space-y-4">
        {messages.length === 0 && !streamingContent && !streaming && (
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

        {messages.map((msg) => {
          if (msg.role === "tool_call") {
            return (
              <div key={msg.message_id} className="flex justify-start">
                <ToolCallInlineMessage
                  tool={msg.tool_name || "unknown"}
                  args={msg.tool_args}
                />
              </div>
            );
          }

          return (
            <div
              key={msg.message_id}
              className={cn(
                "flex",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[75%] max-h-[60vh] overflow-y-auto rounded-2xl px-4 py-3",
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-zinc-800 text-zinc-100 border border-zinc-700"
                )}
              >
                <span
                  className={cn(
                    "text-xs font-medium block mb-1",
                    msg.role === "user" ? "text-blue-200" : "text-zinc-400"
                  )}
                >
                  {msg.role === "user" ? "You" : "Assistant"}
                </span>
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          );
        })}

        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[75%] max-h-[60vh] overflow-y-auto rounded-2xl px-4 py-3 bg-zinc-800 text-zinc-100 border border-zinc-700">
              <span className="text-xs font-medium text-zinc-400 block mb-1">Assistant</span>
              <p className="text-sm whitespace-pre-wrap">{streamingContent}</p>
              <span className="inline-block w-2 h-4 bg-zinc-400 animate-pulse ml-0.5" />
            </div>
          </div>
        )}

        {streaming && !streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-2xl px-4 py-3 bg-zinc-800 text-zinc-100 border border-zinc-700">
              <span className="text-xs font-medium text-zinc-400 block mb-1">Assistant</span>
              <div className="flex items-center gap-1">
                <span className="text-sm text-zinc-400">Thinking</span>
                <span className="flex gap-0.5">
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>
    </ScrollArea>
  );
}
