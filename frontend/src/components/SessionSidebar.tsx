import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type { Session } from "@/types";
import { Pencil, Plus } from "lucide-react";

interface Props {
  sessions: Session[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onUpdateTitle: (sessionId: string, title: string) => void;
  loading: boolean;
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  onUpdateTitle,
  loading,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  const startEditing = (session: Session) => {
    setEditingId(session.session_id);
    setEditValue(session.title);
  };

  const confirmEdit = () => {
    if (editingId && editValue.trim()) {
      onUpdateTitle(editingId, editValue.trim());
    }
    setEditingId(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

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
            sessions.map((s) =>
              editingId === s.session_id ? (
                <Input
                  key={s.session_id}
                  ref={inputRef}
                  value={editValue}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEditValue(e.target.value)}
                  onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                    if (e.key === "Enter") confirmEdit();
                    if (e.key === "Escape") cancelEdit();
                  }}
                  onBlur={confirmEdit}
                  className="h-9 text-sm"
                />
              ) : (
                <Button
                  key={s.session_id}
                  variant={s.session_id === activeSessionId ? "secondary" : "ghost"}
                  onClick={() => onSelect(s.session_id)}
                  onDoubleClick={() => startEditing(s)}
                  className="w-full justify-start text-sm group"
                  size="default"
                >
                  <span className="truncate flex-1 text-left">{s.title}</span>
                  <Pencil
                    className="size-3 shrink-0 opacity-0 group-hover:opacity-70 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      startEditing(s);
                    }}
                  />
                </Button>
              )
            )
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
