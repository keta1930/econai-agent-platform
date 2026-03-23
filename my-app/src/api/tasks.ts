import { api } from "./client";
import type { Task, TaskListResponse, TaskCreateRequest, TaskStatsResponse } from "@/types/task";

export const tasksApi = {
  list: () => api.get<TaskListResponse>("/tasks"),
  get: (taskId: number) => api.get<Task>(`/tasks/${taskId}`),
  create: (data: TaskCreateRequest) => api.post<Task>("/tasks", data),
  stats: (taskId: number) => api.get<TaskStatsResponse>(`/tasks/${taskId}/stats`),
};
