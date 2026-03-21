export function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] rounded-2xl px-4 py-3 bg-card text-card-foreground border border-border">
        <span className="text-xs font-medium text-muted-foreground block mb-1">Assistant</span>
        <div className="flex items-center gap-1">
          <span className="text-sm text-muted-foreground">Thinking</span>
          <span className="flex gap-0.5">
            <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:300ms]" />
          </span>
        </div>
      </div>
    </div>
  );
}
