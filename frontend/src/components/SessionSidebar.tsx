import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { SessionItem } from "@/components/SessionItem";
import type { Session } from "@/types";
import { Plus } from "lucide-react";

interface Props {
  sessions: Session[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onUpdateTitle: (sessionId: string, title: string) => void;
  onDelete: (sessionId: string) => void;
  loading: boolean;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  onUpdateTitle,
  onDelete,
  loading,
}: Props) {
  return (
    <aside className="w-64 bg-sidebar text-sidebar-foreground flex flex-col h-full border-r border-sidebar-border">
      <div className="p-4">
        <Button onClick={onCreate} className="w-full" size="default">
          <Plus className="size-4" />
          New Chat
        </Button>
      </div>

      <Separator />

      <ScrollArea className="flex-1">
        <nav className="p-2 space-y-1">
          {loading ? (
            <p className="text-muted-foreground text-sm p-3">Loading...</p>
          ) : sessions.length === 0 ? (
            <p className="text-muted-foreground text-sm p-3">No chats yet</p>
          ) : (
            sessions.map((s) => (
              <SessionItem
                key={s.session_id}
                session={s}
                active={s.session_id === activeSessionId}
                onSelect={onSelect}
                onUpdateTitle={onUpdateTitle}
                onDelete={onDelete}
              />
            ))
          )}
        </nav>
      </ScrollArea>

      <Separator />

      <div className="p-4 text-xs text-muted-foreground">
        Multi-Tool Chat v1.0
      </div>
    </aside>
  );
}
