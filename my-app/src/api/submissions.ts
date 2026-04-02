import { api } from "./client";
import type {
  SubmissionCreateResponse,
  SubmissionListResponse,
  SubmissionContentResponse,
} from "@/types/submission";

export const submissionsApi = {
  submit: (taskId: number, file: File) => {
    const formData = new FormData();
    formData.append("task_id", String(taskId));
    formData.append("file", file);
    return api.post<SubmissionCreateResponse>("/submissions", formData);
  },
  listMy: () => api.get<SubmissionListResponse>("/submissions/my"),
  getMy: (taskId: number) =>
    api.get<SubmissionListResponse>(`/submissions/my/${taskId}`),
  getStudentSubmissions: (studentId: string) =>
    api.get<SubmissionListResponse>(`/admin/students/${studentId}/submissions`),
  getContent: (submissionId: number) =>
    api.get<SubmissionContentResponse>(`/admin/submissions/${submissionId}/content`),
  getStudentTaskSubmissions: (taskId: number, studentId: string) =>
    api.get<SubmissionListResponse>(
      `/admin/tasks/${taskId}/students/${studentId}/submissions`
    ),
};
