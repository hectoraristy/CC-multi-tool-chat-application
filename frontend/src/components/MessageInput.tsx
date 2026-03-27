import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FileText, Paperclip, Send, Square, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";

const ACCEPTED_TYPES = ".csv,.pdf";

interface Props {
  onSend: (message: string, file?: File) => void;
  disabled: boolean;
  onStop?: () => void;
  streaming: boolean;
  uploading?: boolean;
}

export function MessageInput({ onSend, disabled, onStop, streaming, uploading }: Props) {
  const [input, setInput] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = input.trim();
      if ((!trimmed && !selectedFile) || disabled) return;
      onSend(trimmed || `Analyze the uploaded file`, selectedFile ?? undefined);
      setInput("");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    [input, selectedFile, disabled, onSend]
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

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  }, []);

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-border bg-card p-4"
    >
      <div className="max-w-4xl mx-auto">
        {selectedFile && (
          <div className="flex items-center gap-2 mb-2 px-1">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1 text-sm text-muted-foreground">
              <FileText className="size-3.5" />
              {selectedFile.name}
              <button
                type="button"
                onClick={clearFile}
                className="ml-0.5 rounded-sm hover:bg-background/50 p-0.5"
              >
                <X className="size-3" />
              </button>
            </span>
          </div>
        )}

        <div className="flex items-end gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={handleFileChange}
            className="hidden"
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="shrink-0"
            disabled={(disabled && !streaming) || uploading}
            onClick={() => fileInputRef.current?.click()}
            title="Attach CSV or PDF"
          >
            <Paperclip className="size-4" />
          </Button>

          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={selectedFile ? "Add a message about the file..." : "Type a message..."}
            rows={1}
            disabled={(disabled && !streaming) || uploading}
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
              disabled={disabled || uploading || (!input.trim() && !selectedFile)}
              size="default"
            >
              {uploading ? (
                <>Uploading...</>
              ) : (
                <>
                  <Send className="size-4" />
                  Send
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </form>
  );
}
