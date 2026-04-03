import { api } from "./client";
import type { ClassListResponse, ClassCreateRequest, ClassInfo } from "@/types/class";

export const classesApi = {
  list: () => api.get<ClassListResponse>("/admin/classes"),
  create: (data: ClassCreateRequest) => api.post<ClassInfo>("/admin/classes", data),
  delete: (classId: number) => api.delete<void>(`/admin/classes/${classId}`),
};
