import { useCallback, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { formatArgValue } from "@/lib/utils";
import { getToolResultDownloadUrl } from "@/services/api";

interface Props {
  tool: string;
  args?: Record<string, unknown>;
  sessionId: string;
  resultId?: string;
}

export function ToolCallInlineMessage({ tool, args, sessionId, resultId }: Props) {
  const hasArgs = args && Object.keys(args).length > 0;
  const [downloading, setDownloading] = useState(false);

  const handleDownload = useCallback(async () => {
    if (!resultId) return;
    setDownloading(true);
    try {
      const url = await getToolResultDownloadUrl(sessionId, resultId);
      window.open(url, "_blank", "noopener");
    } catch (err) {
      console.error("Download failed:", err);
    } finally {
      setDownloading(false);
    }
  }, [sessionId, resultId]);

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
      {resultId && (
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-blue-400 hover:text-blue-300 disabled:opacity-50 transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-3.5 h-3.5"
          >
            <path d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z" />
            <path d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z" />
          </svg>
          {downloading ? "Opening..." : "Download full result"}
        </button>
      )}
    </div>
  );
}
