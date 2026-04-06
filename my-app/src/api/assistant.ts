import { api } from "./client";
import type {
  Conversation,
  ConversationDetail,
  ConversationListResponse,
  UploadedFile,
} from "@/types/assistant";

export const assistantApi = {
  createConversation: (title?: string) =>
    api.post<Conversation>("/assistant/conversations", title ? { title } : {}),

  listConversations: () =>
    api.get<ConversationListResponse>("/assistant/conversations"),

  getConversation: (id: string) =>
    api.get<ConversationDetail>(`/assistant/conversations/${id}`),

  deleteConversation: (id: string) =>
    api.delete<void>(`/assistant/conversations/${id}`),

  updateTitle: (id: string, title: string) =>
    api.patch<Conversation>(`/assistant/conversations/${id}`, { title }),

  stopGeneration: (id: string) =>
    api.post<void>(`/assistant/conversations/${id}/stop`),

  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<UploadedFile>("/assistant/upload", form);
  },

  getFilePreviewUrl: (fileId: string) =>
    api.get<{ url: string }>(`/assistant/files/${encodeURIComponent(fileId)}/preview`),
};
