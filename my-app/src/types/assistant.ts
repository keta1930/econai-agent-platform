// ---------------------------------------------------------------------------
// Conversation & Message types
// ---------------------------------------------------------------------------

export type ConversationStatus = "active" | "pending_answer" | "archived";

export interface Conversation {
  id: string;
  title: string | null;
  status: ConversationStatus;
  token_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: Conversation[];
}

// ---------------------------------------------------------------------------
// Message content blocks
// ---------------------------------------------------------------------------

export interface TextBlock {
  type: "text";
  text: string;
}

export interface ToolUseBlock {
  type: "tool_use";
  tool_call_id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface ToolResultBlock {
  type: "tool_result";
  tool_call_id: string;
  content: string;
  is_error: boolean;
}

export interface FileBlock {
  type: "file";
  file_id: string;
  filename: string;
  mime_type: string;
}

export type Block = TextBlock | ToolUseBlock | ToolResultBlock | FileBlock;

export type MessageRole = "user" | "assistant" | "system" | "tool";

export interface Message {
  id: string;
  role: MessageRole;
  content: Block[];
  token_count: number;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

// ---------------------------------------------------------------------------
// StreamingBlock — decoupled streaming state for real-time rendering
// ---------------------------------------------------------------------------

export type StreamingBlockType = "reasoning" | "content" | "tool_calls";

export interface StreamingToolCall {
  id: string;
  name: string;
  displayName: string;
  args: Record<string, unknown>;
  result?: string;
  isError?: boolean;
}

export interface StreamingBlock {
  id: string;
  type: StreamingBlockType;
  content: string;
  toolCalls?: StreamingToolCall[];
  isComplete: boolean;
  timestamp: number;
}

// ---------------------------------------------------------------------------
// Token usage
// ---------------------------------------------------------------------------

export interface TokenUsage {
  total: number;
  max: number;
  ratio: number;
}

/** Fallback when no SSE token_usage event has been received yet */
export const DEFAULT_MAX_CONTEXT = 200_000;

// ---------------------------------------------------------------------------
// File upload
// ---------------------------------------------------------------------------

export interface UploadedFile {
  file_id: string;
  filename: string;
  mime_type: string;
  size: number;
}

// ---------------------------------------------------------------------------
// SSE event types (server → client)
// ---------------------------------------------------------------------------

export interface SSETextDelta {
  type: "text_delta";
  content: string;
}

export interface SSEToolCallStart {
  type: "tool_call_start";
  id: string;
  name: string;
  display_name: string;
}

export interface SSEToolCallArgs {
  type: "tool_call_args";
  id: string;
  args: Record<string, unknown>;
}

export interface SSEToolCallResult {
  type: "tool_call_result";
  id: string;
  result: string;
  is_error: boolean;
}

export interface AskUserQuestion {
  question: string;
  options?: (string | { label: string; description?: string })[];
  select_mode?: "single" | "multiple";
}

export interface SSEAskUser {
  type: "ask_user";
  tool_call_id: string;
  questions: AskUserQuestion[];
}

export interface SSETokenUsage {
  type: "token_usage";
  total_tokens: number;
  max_tokens: number;
  ratio: number;
}

export interface SSEDone {
  type: "done";
}

export interface SSEError {
  type: "error";
  message: string;
}

export interface SSETitleUpdate {
  type: "title_update";
  conversation_id: string;
  title: string;
}

export type SSEEvent =
  | SSETextDelta
  | SSEToolCallStart
  | SSEToolCallArgs
  | SSEToolCallResult
  | SSEAskUser
  | SSETokenUsage
  | SSETitleUpdate
  | SSEDone
  | SSEError;

// ---------------------------------------------------------------------------
// Tool display mapping (tool internal name -> user-facing label + icon)
//
// Labels use business language per naming.md — no technical jargon.
// Icon values are Lucide icon names consumed by the frontend.
// ---------------------------------------------------------------------------

export const TOOL_DISPLAY: Record<string, { label: string; icon: string }> = {
  list_classes:          { label: "获取班级列表",   icon: "School" },
  query_class:           { label: "查询班级数据",   icon: "Database" },
  get_task:              { label: "获取作业信息",   icon: "FileText" },
  query_submissions:     { label: "查询提交记录",   icon: "FileSearch" },
  manage_class:          { label: "班级管理",       icon: "School" },
  manage_task:           { label: "作业管理",       icon: "FileText" },
  manage_topic:          { label: "主题管理",       icon: "MessageSquare" },
  import_roster:         { label: "导入学生名单",   icon: "Upload" },
  read_file:             { label: "读取文件",       icon: "FileSpreadsheet" },
  use_skill:             { label: "加载技能",       icon: "Sparkles" },
  ask_user:              { label: "向用户提问",     icon: "HelpCircle" },
  tavily_search:         { label: "搜索网络",       icon: "Globe" },
};
