import { api } from "./client";
import type {
  Task,
  TaskListResponse,
  TaskDraftRequest,
  TaskUpdateRequest,
  TaskStatsResponse,
  GenerateCriteriaRequest,
  GenerateCriteriaResponse,
} from "@/types/task";

export const tasksApi = {
  list: (status?: string) =>
    api.get<TaskListResponse>(status ? `/tasks?status=${status}` : "/tasks"),
  get: (taskId: number) => api.get<Task>(`/tasks/${taskId}`),
  create: (data: TaskDraftRequest) => api.post<Task>("/tasks", data),
  update: (taskId: number, data: TaskUpdateRequest) =>
    api.patch<Task>(`/tasks/${taskId}`, data),
  delete: (taskId: number) => api.delete<void>(`/tasks/${taskId}`),
  stats: (taskId: number) => api.get<TaskStatsResponse>(`/tasks/${taskId}/stats`),
  generateCriteria: (data: GenerateCriteriaRequest) =>
    api.post<GenerateCriteriaResponse>("/tasks/generate-criteria", data),
};
