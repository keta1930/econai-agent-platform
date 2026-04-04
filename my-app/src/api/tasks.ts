import { api } from "./client";
import type {
  Task,
  TaskListResponse,
  TaskDraftRequest,
  TaskUpdateRequest,
  TaskStatsResponse,
  GenerateCriteriaRequest,
  GenerateCriteriaResponse,
  BatchPublishRequest,
  BatchPublishResponse,
} from "@/types/task";

export const tasksApi = {
  list: (status?: string, classId?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (classId !== undefined) params.set("class_id", String(classId));
    const qs = params.toString();
    return api.get<TaskListResponse>(qs ? `/tasks?${qs}` : "/tasks");
  },
  get: (taskId: string) => api.get<Task>(`/tasks/${taskId}`),
  create: (data: TaskDraftRequest) => api.post<Task>("/tasks", data),
  update: (taskId: string, data: TaskUpdateRequest) =>
    api.patch<Task>(`/tasks/${taskId}`, data),
  delete: (taskId: string) => api.delete<void>(`/tasks/${taskId}`),
  stats: (taskId: string) => api.get<TaskStatsResponse>(`/tasks/${taskId}/stats`),
  generateCriteria: (data: GenerateCriteriaRequest) =>
    api.post<GenerateCriteriaResponse>("/tasks/generate-criteria", data),
  batchPublish: (data: BatchPublishRequest) =>
    api.post<BatchPublishResponse>("/tasks/batch-publish", data),
};
