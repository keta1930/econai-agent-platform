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
  type Block,
  type ToolUseBlock,
  type ToolResultBlock,
  type TextBlock,
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
  | { type: "UPDATE_STREAMING_MESSAGE"; delta: string }
  | {
      type: "ADD_TOOL_CALL";
      toolCall: ToolUseBlock;
    }
  | {
      type: "UPDATE_TOOL_CALL_RESULT";
      id: string;
      result: string;
      isError: boolean;
    }
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
  | { type: "DELETE_CONVERSATION"; id: string }
  | { type: "UPDATE_TOOL_CALL_ARGS"; id: string; args: Record<string, unknown> };

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

/**
 * Find or create the in-progress streaming assistant message.
 *
 * Searches backward because tool_result messages may be appended after the
 * streaming placeholder, so it is not always the last element.
 */
function getOrCreateStreamingMessage(messages: Message[]): {
  messages: Message[];
  index: number;
} {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].id === "__streaming__") {
      return { messages, index: i };
    }
  }
  const placeholder: Message = {
    id: "__streaming__",
    role: "assistant",
    content: [],
    token_count: 0,
    created_at: new Date().toISOString(),
  };
  const updated = [...messages, placeholder];
  return { messages: updated, index: updated.length - 1 };
}

function appendBlockToMessage(message: Message, block: Block): Message {
  return { ...message, content: [...message.content, block] };
}

function replaceMessageAt(messages: Message[], index: number, msg: Message): Message[] {
  const copy = [...messages];
  copy[index] = msg;
  return copy;
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "SET_CONVERSATIONS":
      return { ...state, conversations: action.conversations };

    case "TOUCH_CONVERSATION": {
      return {
        ...state,
        conversations: state.conversations.map((c) =>
          c.id === action.id
            ? { ...c, updated_at: new Date().toISOString() }
            : c,
        ),
      };
    }

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
        // Reset transient state when switching conversations
        isStreaming: false,
        isPendingAnswer: false,
        pendingQuestion: null,
        pendingOptions: null,
        pendingToolCallId: null,
        attachedFiles: [],
      };

    case "APPEND_MESSAGE":
      return { ...state, messages: [...state.messages, action.message] };

    case "UPDATE_STREAMING_MESSAGE": {
      const { messages, index } = getOrCreateStreamingMessage(state.messages);
      let msg = messages[index];

      // Append text to the last text block, or create a new one
      const lastBlock = msg.content[msg.content.length - 1];
      if (lastBlock && lastBlock.type === "text") {
        const updatedBlock: TextBlock = {
          ...lastBlock,
          text: lastBlock.text + action.delta,
        };
        msg = {
          ...msg,
          content: [...msg.content.slice(0, -1), updatedBlock],
        };
      } else {
        msg = appendBlockToMessage(msg, { type: "text", text: action.delta });
      }

      return { ...state, messages: replaceMessageAt(messages, index, msg) };
    }

    case "ADD_TOOL_CALL": {
      const { messages, index } = getOrCreateStreamingMessage(state.messages);
      const msg = appendBlockToMessage(messages[index], action.toolCall);
      return { ...state, messages: replaceMessageAt(messages, index, msg) };
    }

    case "UPDATE_TOOL_CALL_RESULT": {
      // Insert a tool result message after the streaming assistant message
      const toolResultMessage: Message = {
        id: `tool_result_${action.id}`,
        role: "tool",
        content: [
          {
            type: "tool_result",
            tool_call_id: action.id,
            content: action.result,
            is_error: action.isError,
          } satisfies ToolResultBlock,
        ],
        token_count: 0,
        created_at: new Date().toISOString(),
      };
      return { ...state, messages: [...state.messages, toolResultMessage] };
    }

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

    case "UPDATE_TOOL_CALL_ARGS": {
      const msgs = [...state.messages];
      for (let i = msgs.length - 1; i >= 0; i--) {
        const msg = msgs[i];
        if (msg.role !== "assistant") continue;
        const blockIndex = msg.content.findIndex(
          (b): b is ToolUseBlock =>
            b.type === "tool_use" && b.tool_call_id === action.id,
        );
        if (blockIndex !== -1) {
          const updatedContent = [...msg.content];
          updatedContent[blockIndex] = {
            ...(updatedContent[blockIndex] as ToolUseBlock),
            input: action.args,
          };
          msgs[i] = { ...msg, content: updatedContent };
          return { ...state, messages: msgs };
        }
      }
      return state;
    }

    case "DELETE_CONVERSATION": {
      const conversations = state.conversations.filter(
        (c) => c.id !== action.id,
      );
      // If the deleted conversation was active, clear it
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
        };
      }
      return { ...state, conversations };
    }

    default:
      return state;
  }
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
