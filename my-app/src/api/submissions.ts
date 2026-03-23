import { api } from "./client";
import type { SubmissionCreateResponse, SubmissionDetail, SubmissionListResponse } from "@/types/submission";

export const submissionsApi = {
  submit: (taskId: number, file: File) => {
    const formData = new FormData();
    formData.append("task_id", String(taskId));
    formData.append("file", file);
    return api.post<SubmissionCreateResponse>("/submissions", formData);
  },
  listMy: () => api.get<SubmissionListResponse>("/submissions/my"),
  getMy: (taskId: number) => api.get<SubmissionDetail>(`/submissions/my/${taskId}`),
  getStudentSubmissions: (studentId: string) =>
    api.get<SubmissionListResponse>(`/admin/students/${studentId}/submissions`),
};
