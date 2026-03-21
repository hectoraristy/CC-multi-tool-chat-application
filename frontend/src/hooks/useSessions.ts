import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import {
  createSession,
  deleteSession as deleteSessionApi,
  listSessions,
  updateSession,
} from "@/services/api";
import { queryKeys } from "@/lib/queryKeys";
import type { Session } from "@/types";

export function useSessions() {
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const {
    data: sessions = [],
    isLoading: loading,
  } = useQuery<Session[]>({
    queryKey: queryKeys.sessions,
    queryFn: listSessions,
  });

  const createMutation = useMutation({
    mutationFn: (title?: string) => createSession(title),
    onSuccess: (newSession) => {
      queryClient.setQueryData<Session[]>(queryKeys.sessions, (old = []) => [
        newSession,
        ...old,
      ]);
      setActiveSessionId(newSession.session_id);
    },
  });

  const create = useCallback(
    async (title?: string) => {
      return createMutation.mutateAsync(title);
    },
    [createMutation]
  );

  const updateTitleMutation = useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) =>
      updateSession(sessionId, title),
    onMutate: async ({ sessionId, title }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.sessions });
      const previous = queryClient.getQueryData<Session[]>(queryKeys.sessions);
      queryClient.setQueryData<Session[]>(queryKeys.sessions, (old = []) =>
        old.map((s) => (s.session_id === sessionId ? { ...s, title } : s))
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.sessions, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });

  const updateTitle = useCallback(
    async (sessionId: string, title: string) => {
      return updateTitleMutation.mutateAsync({ sessionId, title });
    },
    [updateTitleMutation]
  );

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => deleteSessionApi(sessionId),
    onMutate: async (sessionId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.sessions });
      const previous = queryClient.getQueryData<Session[]>(queryKeys.sessions);
      queryClient.setQueryData<Session[]>(queryKeys.sessions, (old = []) =>
        old.filter((s) => s.session_id !== sessionId)
      );
      if (activeSessionId === sessionId) {
        setActiveSessionId(null);
      }
      return { previous };
    },
    onError: (_err, _sessionId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.sessions, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });

  const deleteSession = useCallback(
    async (sessionId: string) => {
      return deleteMutation.mutateAsync(sessionId);
    },
    [deleteMutation]
  );

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  return {
    sessions,
    activeSessionId,
    loading,
    create,
    selectSession,
    updateTitle,
    deleteSession,
  };
}
