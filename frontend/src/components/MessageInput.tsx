import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Square } from "lucide-react";
import { useCallback, useState } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
  onStop?: () => void;
  streaming: boolean;
}

export function MessageInput({ onSend, disabled, onStop, streaming }: Props) {
  const [input, setInput] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = input.trim();
      if (!trimmed || disabled) return;
      onSend(trimmed);
      setInput("");
    },
    [input, disabled, onSend]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
      }
    },
    [handleSubmit]
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-border bg-card p-4"
    >
      <div className="flex items-end gap-3 max-w-4xl mx-auto">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          rows={1}
          disabled={disabled && !streaming}
          className="flex-1 min-h-10 resize-none"
        />
        {streaming ? (
          <Button
            type="button"
            variant="destructive"
            onClick={onStop}
            size="default"
          >
            <Square className="size-4" />
            Stop
          </Button>
        ) : (
          <Button
            type="submit"
            disabled={disabled || !input.trim()}
            size="default"
          >
            <Send className="size-4" />
            Send
          </Button>
        )}
      </div>
    </form>
  );
}
