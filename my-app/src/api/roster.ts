import { api } from "./client";
import type { RosterListResponse, RosterBatchResponse } from "@/types/roster";

export const rosterApi = {
  list: () => api.get<RosterListResponse>("/admin/roster"),
  add: (studentId: string) => api.post<void>("/admin/roster", { student_id: studentId }),
  batchImport: (studentIds: string[]) =>
    api.post<RosterBatchResponse>("/admin/roster/batch", { student_ids: studentIds }),
  delete: (studentId: string) => api.delete<void>(`/admin/roster/${studentId}`),
};
