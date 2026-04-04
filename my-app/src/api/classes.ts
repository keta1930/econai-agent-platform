import { api } from "./client";
import type { ClassListResponse, ClassCreateRequest, ClassInfo } from "@/types/class";

export const classesApi = {
  list: () => api.get<ClassListResponse>("/admin/classes"),
  create: (data: ClassCreateRequest) => api.post<ClassInfo>("/admin/classes", data),
  delete: (classId: string) => api.delete<void>(`/admin/classes/${classId}`),
  getToken: (classId: string) =>
    api.get<{ join_token: string }>(`/admin/classes/${classId}/token`),
  regenerateToken: (classId: string) =>
    api.post<{ join_token: string }>(`/admin/classes/${classId}/token/regenerate`),
};
