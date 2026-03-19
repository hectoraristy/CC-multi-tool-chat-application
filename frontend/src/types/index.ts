export interface Session {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  message_id: string;
  role: "user" | "assistant" | "tool" | "tool_call";
  content: string;
  tool_name?: string;
  tool_call_id?: string;
  tool_args?: Record<string, unknown>;
  created_at: string;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  id: string;
}

export interface ToolResult {
  tool: string;
  result_preview: string;
}

export interface StreamEvent {
  event: "token" | "tool_call" | "tool_result" | "done" | "error";
  data: string;
}
