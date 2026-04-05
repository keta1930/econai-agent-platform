import {
  createContext,
  useCallback,
  useContext,
  useReducer,
  useState,
  useEffect,
  type ReactNode,
  type Dispatch,
} from "react";
import {
  DEFAULT_MAX_CONTEXT,
  type Conversation,
  type Message,
  type TokenUsage,
  type UploadedFile,
  type StreamingBlock,
  type StreamingBlockType,
  type StreamingToolCall,
} from "@/types/assistant";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  isPendingAnswer: boolean;
  pendingQuestion: string | null;
  pendingOptions: string[] | null;
  pendingToolCallId: string | null;
  tokenUsage: TokenUsage;
  attachedFiles: UploadedFile[];
  streamingBlocks: StreamingBlock[];
}

const initialState: ChatState = {
  conversations: [],
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  isPendingAnswer: false,
  pendingQuestion: null,
  pendingOptions: null,
  pendingToolCallId: null,
  tokenUsage: { total: 0, max: DEFAULT_MAX_CONTEXT, ratio: 0 },
  attachedFiles: [],
  streamingBlocks: [],
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type ChatAction =
  | { type: "SET_CONVERSATIONS"; conversations: Conversation[] }
  | { type: "TOUCH_CONVERSATION"; id: string }
  | { type: "PREPEND_CONVERSATION"; conversation: Conversation }
  | { type: "SET_ACTIVE_CONVERSATION"; id: string | null; messages: Message[] }
  | { type: "APPEND_MESSAGE"; message: Message }
  | { type: "UPDATE_STREAMING_BLOCK"; blockType: StreamingBlockType; delta: string }
  | { type: "UPDATE_STREAMING_TOOL_CALL"; toolCall: Partial<StreamingToolCall> & { id: string } }
  | { type: "UPDATE_STREAMING_TOOL_RESULT"; id: string; result: string; isError: boolean }
  | { type: "FINALIZE_STREAM" }
  | { type: "UPDATE_CONVERSATION_TITLE"; conversationId: string; title: string }
  | {
      type: "SET_PENDING_ANSWER";
      toolCallId: string;
      question: string;
      options?: string[];
    }
  | { type: "CLEAR_PENDING_ANSWER" }
  | { type: "SET_STREAMING"; isStreaming: boolean }
  | { type: "SET_TOKEN_USAGE"; usage: TokenUsage }
  | { type: "ATTACH_FILE"; file: UploadedFile }
  | { type: "REMOVE_FILE"; fileId: string }
  | { type: "CLEAR_FILES" }
  | { type: "DELETE_CONVERSATION"; id: string };

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "SET_CONVERSATIONS":
      return { ...state, conversations: action.conversations };

    case "TOUCH_CONVERSATION":
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.id
            ? { ...c, updated_at: new Date().toISOString() }
            : c,
        ),
      };

    case "PREPEND_CONVERSATION":
      return {
        ...state,
        conversations: [action.conversation, ...state.conversations],
      };

    case "SET_ACTIVE_CONVERSATION":
      return {
        ...state,
        activeConversationId: action.id,
        messages: action.messages,
        isStreaming: false,
        isPendingAnswer: false,
        pendingQuestion: null,
        pendingOptions: null,
        pendingToolCallId: null,
        attachedFiles: [],
        streamingBlocks: [],
        tokenUsage: { total: 0, max: DEFAULT_MAX_CONTEXT, ratio: 0 },
      };

    case "APPEND_MESSAGE":
      return { ...state, messages: [...state.messages, action.message] };

    case "UPDATE_STREAMING_BLOCK": {
      const blocks = [...state.streamingBlocks];
      const lastIdx = findLastIndex(
        blocks,
        (b) => b.type === action.blockType && !b.isComplete,
      );
      if (lastIdx >= 0) {
        blocks[lastIdx] = {
          ...blocks[lastIdx],
          content: blocks[lastIdx].content + action.delta,
        };
      } else {
        blocks.push({
          id: `block_${Date.now()}_${blocks.length}`,
          type: action.blockType,
          content: action.delta,
          isComplete: false,
          timestamp: Date.now(),
        });
      }
      return { ...state, streamingBlocks: blocks };
    }

    case "UPDATE_STREAMING_TOOL_CALL": {
      const blocks = [...state.streamingBlocks];
      // Complete all reasoning/content blocks when a tool call arrives
      for (let i = 0; i < blocks.length; i++) {
        if ((blocks[i].type === "reasoning" || blocks[i].type === "content") && !blocks[i].isComplete) {
          blocks[i] = { ...blocks[i], isComplete: true };
        }
      }
      // Find or create tool_calls block
      let tcIdx = findLastIndex(blocks, (b) => b.type === "tool_calls" && !b.isComplete);
      if (tcIdx < 0) {
        blocks.push({
          id: `block_tc_${Date.now()}`,
          type: "tool_calls",
          content: "",
          toolCalls: [],
          isComplete: false,
          timestamp: Date.now(),
        });
        tcIdx = blocks.length - 1;
      }
      const tcBlock = blocks[tcIdx];
      const existingCalls = tcBlock.toolCalls ?? [];
      const existingCallIdx = existingCalls.findIndex((tc) => tc.id === action.toolCall.id);
      if (existingCallIdx >= 0) {
        // Merge only defined fields — partial updates (e.g. tool_call_args) must not
        // overwrite fields set by earlier events (e.g. tool_call_start's name/displayName)
        const merged = { ...existingCalls[existingCallIdx] };
        for (const [k, v] of Object.entries(action.toolCall)) {
          if (v !== undefined) (merged as Record<string, unknown>)[k] = v;
        }
        const updated = [...existingCalls];
        updated[existingCallIdx] = merged;
        blocks[tcIdx] = { ...tcBlock, toolCalls: updated };
      } else {
        blocks[tcIdx] = { ...tcBlock, toolCalls: [...existingCalls, action.toolCall as StreamingToolCall] };
      }
      return { ...state, streamingBlocks: blocks };
    }

    case "UPDATE_STREAMING_TOOL_RESULT": {
      const blocks = state.streamingBlocks.map((b) => {
        if (b.type !== "tool_calls" || !b.toolCalls) return b;
        const updated = b.toolCalls.map((tc) =>
          tc.id === action.id ? { ...tc, result: action.result, isError: action.isError } : tc,
        );
        return { ...b, toolCalls: updated };
      });
      return { ...state, streamingBlocks: blocks };
    }

    case "FINALIZE_STREAM":
      return { ...state, streamingBlocks: [] };

    case "UPDATE_CONVERSATION_TITLE":
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.conversationId ? { ...c, title: action.title } : c,
        ),
      };

    case "SET_PENDING_ANSWER":
      return {
        ...state,
        isPendingAnswer: true,
        pendingQuestion: action.question,
        pendingOptions: action.options ?? null,
        pendingToolCallId: action.toolCallId,
      };

    case "CLEAR_PENDING_ANSWER":
      return {
        ...state,
        isPendingAnswer: false,
        pendingQuestion: null,
        pendingOptions: null,
        pendingToolCallId: null,
      };

    case "SET_STREAMING":
      return { ...state, isStreaming: action.isStreaming };

    case "SET_TOKEN_USAGE":
      return { ...state, tokenUsage: action.usage };

    case "ATTACH_FILE":
      return { ...state, attachedFiles: [...state.attachedFiles, action.file] };

    case "REMOVE_FILE":
      return {
        ...state,
        attachedFiles: state.attachedFiles.filter(
          (f) => f.file_id !== action.fileId,
        ),
      };

    case "CLEAR_FILES":
      return { ...state, attachedFiles: [] };

    case "DELETE_CONVERSATION": {
      const conversations = state.conversations.filter(
        (c) => c.id !== action.id,
      );
      if (state.activeConversationId === action.id) {
        return {
          ...state,
          conversations,
          activeConversationId: null,
          messages: [],
          isPendingAnswer: false,
          pendingQuestion: null,
          pendingOptions: null,
          pendingToolCallId: null,
          streamingBlocks: [],
        };
      }
      return { ...state, conversations };
    }

    default:
      return state;
  }
}

/** Array.findLastIndex polyfill for environments that lack it */
function findLastIndex<T>(arr: T[], predicate: (item: T) => boolean): number {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (predicate(arr[i])) return i;
  }
  return -1;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface ChatContextValue {
  state: ChatState;
  dispatch: Dispatch<ChatAction>;
  isPanelOpen: boolean;
  togglePanel: () => void;
  openPanel: () => void;
  closePanel: () => void;
}

const PANEL_STORAGE_KEY = "chatPanelOpen";

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  const [isPanelOpen, setIsPanelOpen] = useState<boolean>(() => {
    const stored = localStorage.getItem(PANEL_STORAGE_KEY);
    return stored === "true";
  });

  // Persist panel state changes to localStorage
  useEffect(() => {
    localStorage.setItem(PANEL_STORAGE_KEY, String(isPanelOpen));
  }, [isPanelOpen]);

  const togglePanel = useCallback(() => setIsPanelOpen((prev) => !prev), []);
  const openPanel = useCallback(() => setIsPanelOpen(true), []);
  const closePanel = useCallback(() => setIsPanelOpen(false), []);

  return (
    <ChatContext
      value={{ state, dispatch, isPanelOpen, togglePanel, openPanel, closePanel }}
    >
      {children}
    </ChatContext>
  );
}

export function useChatContext(): ChatContextValue {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
