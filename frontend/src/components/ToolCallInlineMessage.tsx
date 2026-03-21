import { Badge } from "@/components/ui/badge";

interface Props {
  tool: string;
  args?: Record<string, unknown>;
}

function formatArgValue(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function ToolCallInlineMessage({ tool, args }: Props) {
  const hasArgs = args && Object.keys(args).length > 0;

  return (
    <div className="max-w-[75%] max-h-[60vh] overflow-y-auto rounded-2xl px-4 py-3 bg-amber-900/30 border border-amber-700/40 text-amber-100">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs text-amber-300/70">Calling</span>
        <Badge variant="outline" className="font-mono text-xs px-1.5 py-0 border-amber-700/50 text-amber-200">
          {tool}
        </Badge>
      </div>
      {hasArgs && (
        <div className="mt-1.5 space-y-0.5">
          {Object.entries(args).map(([key, value]) => (
            <div key={key} className="flex gap-2 text-xs">
              <span className="font-mono text-amber-300/60 shrink-0">
                {key}:
              </span>
              <pre className="font-mono text-amber-100/70 whitespace-pre-wrap break-all">
                {formatArgValue(value)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
