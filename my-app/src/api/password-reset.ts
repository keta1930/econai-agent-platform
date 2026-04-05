import { api } from "./client";
import type {
  PasswordResetListResponse,
  PasswordResetCountResponse,
  PasswordResetApproveResponse,
} from "@/types/password-reset";

export const passwordResetApi = {
  forgotPassword: (username: string) =>
    api.post<{ message: string }>("/auth/forgot-password", { username }),

  list: (classId: string) =>
    api.get<PasswordResetListResponse>(
      `/admin/classes/${classId}/password-reset-requests`,
    ),

  count: (classId: string) =>
    api.get<PasswordResetCountResponse>(
      `/admin/classes/${classId}/password-reset-requests/count`,
    ),

  approve: (classId: string, requestIds: string[]) =>
    api.post<PasswordResetApproveResponse>(
      `/admin/classes/${classId}/password-reset-requests/approve`,
      { request_ids: requestIds },
    ),
};
