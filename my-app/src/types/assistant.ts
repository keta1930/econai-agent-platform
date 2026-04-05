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

export interface SSEAskUser {
  type: "ask_user";
  tool_call_id: string;
  question: string;
  options?: string[];
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

export type SSEEvent =
  | SSETextDelta
  | SSEToolCallStart
  | SSEToolCallArgs
  | SSEToolCallResult
  | SSEAskUser
  | SSETokenUsage
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
  list_tasks:            { label: "查询作业列表",   icon: "ClipboardList" },
  get_task_detail:       { label: "获取作业详情",   icon: "FileText" },
  get_task_stats:        { label: "查询作业统计",   icon: "BarChart3" },
  list_roster:           { label: "获取学生名单",   icon: "Users" },
  get_student_submissions: { label: "查看学生提交", icon: "FileCheck" },
  get_submission_content:  { label: "读取提交内容", icon: "Eye" },
  list_sharing_topics:   { label: "查询分享主题",   icon: "MessageSquare" },
  create_task:           { label: "创建作业",       icon: "FilePlus" },
  publish_task:          { label: "发布作业",       icon: "Send" },
  create_sharing_topic:  { label: "创建分享主题",   icon: "PlusCircle" },
  import_roster:         { label: "导入学生名单",   icon: "Upload" },
  ask_user:              { label: "向用户提问",     icon: "HelpCircle" },
  tavily_search:         { label: "搜索网络",       icon: "Globe" },
  parse_uploaded_file:   { label: "解析上传文件",   icon: "FileSpreadsheet" },
};
