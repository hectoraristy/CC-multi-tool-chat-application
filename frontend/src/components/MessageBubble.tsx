import React from "react";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";

interface Props {
  message: ChatMessage;
}

export const MessageBubble = React.memo(function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] max-h-[60vh] overflow-y-auto rounded-2xl px-4 py-3",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-card text-card-foreground border border-border"
        )}
      >
        <span
          className={cn(
            "text-xs font-medium block mb-1",
            isUser ? "text-primary-foreground/70" : "text-muted-foreground"
          )}
        >
          {isUser ? "You" : "Assistant"}
        </span>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
});
