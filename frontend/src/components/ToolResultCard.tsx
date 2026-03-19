import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface Props {
  tool: string;
  args?: Record<string, unknown>;
  status: "calling" | "done";
  preview?: string;
}

function formatArgValue(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function ToolResultCard({ tool, args, status, preview }: Props) {
  const hasArgs = args && Object.keys(args).length > 0;

  return (
    <Card className="my-2 gap-0 py-0 overflow-hidden">
      <CardHeader className="flex-row items-center gap-2 px-3 py-2 border-b border-border">
        <span className="text-xs font-mono text-primary">{tool}</span>
        {status === "calling" ? (
          <Badge variant="outline" className="animate-pulse text-yellow-400 border-yellow-400/30">
            Running...
          </Badge>
        ) : (
          <Badge variant="secondary" className="text-green-400">
            Done
          </Badge>
        )}
      </CardHeader>

      {hasArgs && (
        <CardContent className="px-3 py-2 border-b border-border">
          <div className="space-y-1">
            {Object.entries(args).map(([key, value]) => (
              <div key={key} className="flex gap-2 text-xs">
                <span className="font-mono text-muted-foreground shrink-0">{key}:</span>
                <pre className="font-mono text-foreground/80 whitespace-pre-wrap break-all">
                  {formatArgValue(value)}
                </pre>
              </div>
            ))}
          </div>
        </CardContent>
      )}

      {preview && (
        <CardContent className="px-3 py-2">
          <pre className="text-xs text-muted-foreground whitespace-pre-wrap max-h-40 overflow-y-auto">
            {preview}
          </pre>
        </CardContent>
      )}
    </Card>
  );
}
