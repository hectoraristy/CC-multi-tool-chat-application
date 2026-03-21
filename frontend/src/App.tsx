import { ChatWindow } from "@/components/ChatWindow";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { SessionSidebar } from "@/components/SessionSidebar";
import { useSessions } from "@/hooks/useSessions";

export default function App() {
  const { sessions, activeSessionId, loading, create, selectSession, updateTitle, deleteSession } =
    useSessions();

  return (
    <div className="dark flex h-screen bg-background text-foreground">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={selectSession}
        onCreate={() => create()}
        onUpdateTitle={updateTitle}
        onDelete={deleteSession}
        loading={loading}
      />
      <ErrorBoundary>
        <ChatWindow sessionId={activeSessionId} />
      </ErrorBoundary>
    </div>
  );
}
