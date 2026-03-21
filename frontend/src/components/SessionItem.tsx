import React from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useInlineEdit } from "@/hooks/useInlineEdit";
import type { Session } from "@/types";
import { Pencil, Trash2 } from "lucide-react";

interface Props {
  session: Session;
  active: boolean;
  onSelect: (id: string) => void;
  onUpdateTitle: (sessionId: string, title: string) => void;
  onDelete: (sessionId: string) => void;
}

export const SessionItem = React.memo(function SessionItem({
  session,
  active,
  onSelect,
  onUpdateTitle,
  onDelete,
}: Props) {
  const { editing, value, setValue, inputRef, start, confirm, cancel } =
    useInlineEdit((newTitle) => onUpdateTitle(session.session_id, newTitle));

  if (editing) {
    return (
      <Input
        ref={inputRef}
        value={value}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(e.target.value)}
        onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
          if (e.key === "Enter") confirm();
          if (e.key === "Escape") cancel();
        }}
        onBlur={confirm}
        className="h-9 text-sm"
      />
    );
  }

  return (
    <div className="relative flex items-center group">
      <Button
        variant={active ? "secondary" : "ghost"}
        onClick={() => onSelect(session.session_id)}
        onDoubleClick={() => start(session.title)}
        className="w-full justify-start text-sm pr-14"
        size="default"
      >
        <span className="truncate flex-1 text-left">{session.title}</span>
      </Button>
      <div className="absolute right-1 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          className="p-1 rounded hover:bg-accent"
          onClick={() => start(session.title)}
        >
          <Pencil className="size-4 text-muted-foreground" />
        </button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <button
              type="button"
              className="p-1 rounded hover:bg-destructive/20"
            >
              <Trash2 className="size-4 text-destructive" />
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete chat?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete this chat and all its messages.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => onDelete(session.session_id)}
                className="bg-destructive text-white hover:bg-destructive/90"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
});
