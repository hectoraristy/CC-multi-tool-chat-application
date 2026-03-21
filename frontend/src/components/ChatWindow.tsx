import { useChat } from "@/hooks/useChat";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

interface Props {
  sessionId: string | null;
}

export function ChatWindow({ sessionId }: Props) {
  const {
    messages,
    streaming,
    streamingContent,
    sendMessage,
    stopStreaming,
  } = useChat(sessionId);

  if (!sessionId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background text-muted-foreground">
        <div className="text-center">
          <h2 className="text-2xl font-semibold mb-2">Welcome</h2>
          <p className="text-sm">
            Create a new chat or select an existing one to get started.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-background h-full min-h-0">
      <MessageList
        messages={messages}
        streamingContent={streamingContent}
        streaming={streaming}
      />

      <MessageInput
        onSend={sendMessage}
        disabled={streaming}
        onStop={stopStreaming}
        streaming={streaming}
      />
    </div>
  );
}
