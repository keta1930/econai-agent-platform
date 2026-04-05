import { useCallback, useRef } from "react";
import { flushSync } from "react-dom";
import { toast } from "sonner";
import { useChatContext, type ChatAction } from "@/contexts/ChatContext";
import { assistantApi } from "@/api/assistant";
import { streamChat, streamAnswer } from "@/api/stream";
import {
  DEFAULT_MAX_CONTEXT,
  type ConversationDetail,
  type Message,
  type SSEEvent,
  type UploadedFile,
} from "@/types/assistant";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * If a conversation is in "pending_answer" status, find the last ask_user
 * tool_use block and dispatch SET_PENDING_ANSWER to restore the UI state.
 * Used by both refetchConversation and selectConversation.
 */
function restorePendingAnswerIfNeeded(
  detail: ConversationDetail,
  dispatch: React.Dispatch<ChatAction>,
): void {
  if (detail.status !== "pending_answer") return;

  for (let i = detail.messages.length - 1; i >= 0; i--) {
    const msg = detail.messages[i];
    if (msg.role !== "assistant") continue;
    for (let j = msg.content.length - 1; j >= 0; j--) {
      const block = msg.content[j];
      if (block.type === "tool_use" && block.name === "ask_user") {
        const input = block.input as { question?: string; options?: string[] };
        dispatch({
          type: "SET_PENDING_ANSWER",
          toolCallId: block.tool_call_id,
          question: input.question ?? "",
          options: input.options,
        });
        return;
      }
    }
  }
}

// ---------------------------------------------------------------------------
// useChat — orchestrates chat actions and SSE stream consumption
// ---------------------------------------------------------------------------

export function useChat() {
  const { state, dispatch } = useChatContext();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Ref tracks the latest attachedFiles so sendMessage never captures a stale snapshot
  const attachedFilesRef = useRef(state.attachedFiles);
  attachedFilesRef.current = state.attachedFiles;

  // -------------------------------------------------------------------
  // SSE stream processor (shared between sendMessage and answerQuestion)
  // -------------------------------------------------------------------

  const processStream = useCallback(
    async (stream: AsyncGenerator<SSEEvent>) => {
      dispatch({ type: "SET_STREAMING", isStreaming: true });

      try {
        for await (const event of stream) {
          switch (event.type) {
            case "text_delta":
              flushSync(() => {
                dispatch({
                  type: "UPDATE_STREAMING_BLOCK",
                  blockType: "content",
                  delta: event.content,
                });
              });
              break;

            case "tool_call_start":
              dispatch({
                type: "UPDATE_STREAMING_TOOL_CALL",
                toolCall: {
                  id: event.id,
                  name: event.name,
                  displayName: event.display_name,
                  args: {},
                },
              });
              break;

            case "tool_call_args":
              dispatch({
                type: "UPDATE_STREAMING_TOOL_CALL",
                toolCall: {
                  id: event.id,
                  args: event.args,
                },
              });
              break;

            case "tool_call_result":
              dispatch({
                type: "UPDATE_STREAMING_TOOL_RESULT",
                id: event.id,
                result: event.result,
                isError: event.is_error,
              });
              break;

            case "ask_user":
              dispatch({
                type: "SET_PENDING_ANSWER",
                toolCallId: event.tool_call_id,
                question: event.question,
                options: event.options,
              });
              break;

            case "token_usage":
              dispatch({
                type: "SET_TOKEN_USAGE",
                usage: {
                  total: event.total_tokens,
                  max: event.max_tokens,
                  ratio: event.ratio,
                },
              });
              break;

            case "title_update":
              dispatch({
                type: "UPDATE_CONVERSATION_TITLE",
                conversationId: event.conversation_id,
                title: event.title,
              });
              break;

            case "done":
              break;

            case "error":
              throw new Error(event.message);
          }
        }
      } catch (err) {
        // AbortError is expected when user stops generation — not a real error
        if (err instanceof DOMException && err.name === "AbortError") return;
        throw err;
      } finally {
        dispatch({ type: "SET_STREAMING", isStreaming: false });
        // Do NOT dispatch FINALIZE_STREAM here — SET_ACTIVE_CONVERSATION (from refetch)
        // already resets streamingBlocks. Clearing here would cause a flash of empty content
        // between stream end and refetch completion. If refetch fails, streaming blocks are
        // preserved as degraded display so the user doesn't lose the response.
        abortControllerRef.current = null;
      }
    },
    [dispatch],
  );

  // -------------------------------------------------------------------
  // Refetch conversation detail to replace streaming blocks with persisted data
  // -------------------------------------------------------------------

  const refetchConversation = useCallback(
    async (conversationId: string) => {
      try {
        const detail = await assistantApi.getConversation(conversationId);
        dispatch({
          type: "SET_ACTIVE_CONVERSATION",
          id: detail.id,
          messages: detail.messages,
        });
        // Restore pending answer state if the conversation is waiting for user input
        restorePendingAnswerIfNeeded(detail, dispatch);
        if (detail.token_count > 0) {
          dispatch({
            type: "SET_TOKEN_USAGE",
            usage: {
              total: detail.token_count,
              max: DEFAULT_MAX_CONTEXT,
              ratio: detail.token_count / DEFAULT_MAX_CONTEXT,
            },
          });
        }
      } catch (err) {
        // Refetch failed — streaming blocks are preserved as degraded display
        console.warn("[useChat] refetch failed, keeping streaming blocks as fallback:", err);
      }
    },
    [dispatch],
  );

  // -------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------

  const sendMessage = useCallback(
    async (content: string, classId?: string) => {
      const conversationId = state.activeConversationId;
      if (!conversationId) return;

      // Snapshot files from ref to avoid stale closure
      const files = attachedFilesRef.current;

      // Optimistic: add user message to local state immediately
      const userMessage: Message = {
        id: `local_${Date.now()}`,
        role: "user",
        content: [
          { type: "text", text: content },
          ...files.map((f) => ({
            type: "file" as const,
            file_id: f.file_id,
            filename: f.filename,
            mime_type: f.mime_type,
          })),
        ],
        token_count: 0,
        created_at: new Date().toISOString(),
      };
      dispatch({ type: "APPEND_MESSAGE", message: userMessage });
      dispatch({ type: "TOUCH_CONVERSATION", id: conversationId });
      dispatch({ type: "CLEAR_FILES" });

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const body: { content: string; class_id?: string; files?: Array<{ file_id: string; filename: string; mime_type: string }> } = { content };
      if (classId) body.class_id = classId;
      if (files.length > 0) body.files = files.map((f) => ({
        file_id: f.file_id,
        filename: f.filename,
        mime_type: f.mime_type,
      }));

      const stream = streamChat(conversationId, body, controller.signal);
      try {
        await processStream(stream);
        await refetchConversation(conversationId);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        toast.error(err instanceof Error ? err.message : "发送失败，请重试");
      }
    },
    [state.activeConversationId, dispatch, processStream, refetchConversation],
  );

  const answerQuestion = useCallback(
    async (answer: string) => {
      const conversationId = state.activeConversationId;
      if (!conversationId) return;

      dispatch({ type: "CLEAR_PENDING_ANSWER" });

      // Add the user's answer as a visible message
      const answerMessage: Message = {
        id: `answer_${Date.now()}`,
        role: "user",
        content: [{ type: "text", text: answer }],
        token_count: 0,
        created_at: new Date().toISOString(),
      };
      dispatch({ type: "APPEND_MESSAGE", message: answerMessage });

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const stream = streamAnswer(conversationId, answer, controller.signal);
      try {
        await processStream(stream);
        await refetchConversation(conversationId);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        toast.error(err instanceof Error ? err.message : "发送失败，请重试");
      }
    },
    [state.activeConversationId, dispatch, processStream, refetchConversation],
  );

  const stopGeneration = useCallback(async () => {
    // Abort the client-side fetch
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    // Notify the server to stop the agent loop
    const conversationId = state.activeConversationId;
    if (conversationId) {
      await assistantApi.stopGeneration(conversationId).catch(() => {
        // Best-effort — the abort above already cancelled the stream
      });
    }

    dispatch({ type: "SET_STREAMING", isStreaming: false });
  }, [state.activeConversationId, dispatch]);

  const loadConversations = useCallback(async () => {
    const res = await assistantApi.listConversations();
    dispatch({ type: "SET_CONVERSATIONS", conversations: res.conversations });
  }, [dispatch]);

  const selectConversation = useCallback(
    async (id: string) => {
      const detail = await assistantApi.getConversation(id);
      dispatch({
        type: "SET_ACTIVE_CONVERSATION",
        id: detail.id,
        messages: detail.messages,
      });

      // Restore pending answer state if the conversation is waiting
      restorePendingAnswerIfNeeded(detail, dispatch);

      // Restore token usage from conversation-level data.
      // The real max comes from SSE token_usage events during streaming;
      // DEFAULT_MAX_CONTEXT is the fallback until the next stream updates it.
      if (detail.token_count > 0) {
        dispatch({
          type: "SET_TOKEN_USAGE",
          usage: {
            total: detail.token_count,
            max: DEFAULT_MAX_CONTEXT,
            ratio: detail.token_count / DEFAULT_MAX_CONTEXT,
          },
        });
      }
    },
    [dispatch],
  );

  const createConversation = useCallback(async () => {
    const conversation = await assistantApi.createConversation();
    dispatch({ type: "PREPEND_CONVERSATION", conversation });
    dispatch({
      type: "SET_ACTIVE_CONVERSATION",
      id: conversation.id,
      messages: [],
    });
    return conversation;
  }, [dispatch]);

  const deleteConversation = useCallback(
    async (id: string) => {
      await assistantApi.deleteConversation(id);
      dispatch({ type: "DELETE_CONVERSATION", id });
    },
    [dispatch],
  );

  const uploadFile = useCallback(
    async (file: File): Promise<UploadedFile> => {
      const uploaded = await assistantApi.uploadFile(file);
      dispatch({ type: "ATTACH_FILE", file: uploaded });
      return uploaded;
    },
    [dispatch],
  );

  const removeAttachment = useCallback(
    (fileId: string) => {
      dispatch({ type: "REMOVE_FILE", fileId });
    },
    [dispatch],
  );

  return {
    state,
    sendMessage,
    answerQuestion,
    stopGeneration,
    loadConversations,
    selectConversation,
    createConversation,
    deleteConversation,
    uploadFile,
    removeAttachment,
  };
}
