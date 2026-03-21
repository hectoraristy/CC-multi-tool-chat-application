export function EmptyState() {
  return (
    <div className="flex items-center justify-center h-full min-h-[50vh]">
      <div className="text-center text-muted-foreground">
        <h2 className="text-xl font-semibold mb-2">Multi-Tool Chat</h2>
        <p className="text-sm">
          Ask me anything. I can query databases, fetch web pages, call
          APIs, and read files.
        </p>
      </div>
    </div>
  );
}
