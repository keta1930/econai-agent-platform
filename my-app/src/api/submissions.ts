import { api } from "./client";
import type {
  SubmissionCreateResponse,
  SubmissionListResponse,
  SubmissionContentResponse,
} from "@/types/submission";

export const submissionsApi = {
  submit: (
    taskId: number,
    contentType: "text" | "file" | "image",
    payload: string | File,
  ) => {
    const formData = new FormData();
    formData.append("task_id", String(taskId));
    formData.append("content_type", contentType);

    if (contentType === "text") {
      formData.append("text_content", payload as string);
    } else {
      formData.append("file", payload as File);
    }

    return api.post<SubmissionCreateResponse>("/submissions", formData);
  },
  listMy: () => api.get<SubmissionListResponse>("/submissions/my"),
  getMy: (taskId: number) =>
    api.get<SubmissionListResponse>(`/submissions/my/${taskId}`),
  getStudentSubmissions: (studentId: number) =>
    api.get<SubmissionListResponse>(`/admin/students/${studentId}/submissions`),
  getContent: (submissionId: number) =>
    api.get<SubmissionContentResponse>(`/admin/submissions/${submissionId}/content`),
  getStudentTaskSubmissions: (taskId: number, studentId: number) =>
    api.get<SubmissionListResponse>(
      `/admin/tasks/${taskId}/students/${studentId}/submissions`
    ),
};
