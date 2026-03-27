export interface Session {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface FileAttachment {
  s3_uri: string;
  filename: string;
  file_type: "csv" | "pdf";
  size_bytes: number;
}

export interface ChatMessage {
  message_id: string;
  role: "user" | "assistant" | "tool" | "tool_call";
  content: string;
  tool_name?: string;
  tool_call_id?: string;
  tool_args?: Record<string, unknown>;
  result_id?: string;
  attachments?: FileAttachment[];
  created_at: string;
}

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  id: string;
}
