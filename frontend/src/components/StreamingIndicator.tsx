interface Props {
  content: string;
}

export function StreamingIndicator({ content }: Props) {
  if (!content) return null;

  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] max-h-[60vh] overflow-y-auto rounded-2xl px-4 py-3 bg-card text-card-foreground border border-border">
        <span className="text-xs font-medium text-muted-foreground block mb-1">Assistant</span>
        <p className="text-sm whitespace-pre-wrap">{content}</p>
        <span className="inline-block w-2 h-4 bg-muted-foreground animate-pulse ml-0.5" />
      </div>
    </div>
  );
}
