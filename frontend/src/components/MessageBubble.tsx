import React from "react";
import { FileSpreadsheet, FileText } from "lucide-react";
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

        {isUser && message.attachments?.length ? (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {message.attachments.map((att) => (
              <span
                key={att.s3_uri}
                className="inline-flex items-center gap-1 rounded-md bg-primary-foreground/15 px-2 py-0.5 text-xs"
              >
                {att.file_type === "csv" ? (
                  <FileSpreadsheet className="size-3" />
                ) : (
                  <FileText className="size-3" />
                )}
                {att.filename}
              </span>
            ))}
          </div>
        ) : null}

        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
});
