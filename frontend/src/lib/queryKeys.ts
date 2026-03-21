export const queryKeys = {
  sessions: ["sessions"] as const,
  messages: (sessionId: string) => ["messages", sessionId] as const,
};
