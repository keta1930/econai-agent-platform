import { api } from "./client";
import type {
  RosterListResponse,
  RosterBatchResponse,
  RosterBatchDeleteResponse,
  MemberBatchRemoveResponse,
} from "@/types/roster";

export const rosterApi = {
  list: (classId: string) =>
    api.get<RosterListResponse>(`/admin/classes/${classId}/roster`),
  add: (classId: string, studentId: string) =>
    api.post<void>(`/admin/classes/${classId}/roster`, { student_id: studentId }),
  batchImport: (classId: string, studentIds: string[]) =>
    api.post<RosterBatchResponse>(`/admin/classes/${classId}/roster/batch`, {
      student_ids: studentIds,
    }),
  delete: (classId: string, studentId: string) =>
    api.delete<void>(`/admin/classes/${classId}/roster/${studentId}`),
  batchDelete: (classId: string, studentIds: string[]) =>
    api.post<RosterBatchDeleteResponse>(
      `/admin/classes/${classId}/roster/batch-delete`,
      { student_ids: studentIds },
    ),
  resetPassword: (classId: string, userId: string, newPassword: string) =>
    api.post<void>(`/admin/classes/${classId}/roster/reset-password`, {
      user_id: userId,
      new_password: newPassword,
    }),
  removeMember: (classId: string, userId: string) =>
    api.delete<void>(`/admin/classes/${classId}/members/${userId}`),
  batchRemoveMembers: (classId: string, userIds: string[]) =>
    api.post<MemberBatchRemoveResponse>(
      `/admin/classes/${classId}/members/batch-remove`,
      { user_ids: userIds },
    ),
};
