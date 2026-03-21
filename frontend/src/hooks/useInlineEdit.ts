import { useCallback, useEffect, useRef, useState } from "react";

export function useInlineEdit(onConfirm: (value: string) => void) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const start = useCallback((initialValue: string) => {
    setValue(initialValue);
    setEditing(true);
  }, []);

  const confirm = useCallback(() => {
    if (value.trim()) {
      onConfirm(value.trim());
    }
    setEditing(false);
  }, [value, onConfirm]);

  const cancel = useCallback(() => {
    setEditing(false);
  }, []);

  return { editing, value, setValue, inputRef, start, confirm, cancel };
}
