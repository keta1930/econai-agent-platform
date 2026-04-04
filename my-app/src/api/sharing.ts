import { api } from "./client";
import type {
  TopicListResponse,
  TopicMaterialsResponse,
  VoteResponse,
  AdminTopicListResponse,
  AdminTopicListItem,
  TopicCreateRequest,
  TopicUpdateRequest,
  TopicSuggestRequest,
} from "@/types/sharing";

export const sharingApi = {
  list: (status?: string) =>
    api.get<TopicListResponse>(status ? `/sharing/topics?status=${status}` : "/sharing/topics"),
  getMaterials: (topicId: string) =>
    api.get<TopicMaterialsResponse>(`/sharing/topics/${topicId}/materials`),
  vote: (topicId: string) =>
    api.post<VoteResponse>(`/sharing/topics/${topicId}/vote`),
  unvote: (topicId: string) =>
    api.delete<VoteResponse>(`/sharing/topics/${topicId}/vote`),
  suggest: (data: TopicSuggestRequest) =>
    api.post<VoteResponse>("/sharing/topics/suggest", data),
};

export const adminSharingApi = {
  list: (status?: string, classId?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (classId !== undefined) params.set("class_id", String(classId));
    const qs = params.toString();
    return api.get<AdminTopicListResponse>(
      qs ? `/admin/sharing/topics?${qs}` : "/admin/sharing/topics"
    );
  },
  create: (data: TopicCreateRequest) =>
    api.post<AdminTopicListItem>("/admin/sharing/topics", data),
  update: (topicId: string, data: TopicUpdateRequest) =>
    api.patch<AdminTopicListItem>(`/admin/sharing/topics/${topicId}`, data),
  delete: (topicId: string) =>
    api.delete<void>(`/admin/sharing/topics/${topicId}`),
};
